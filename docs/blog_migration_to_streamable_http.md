# 从 SSE 到 Streamable HTTP：MCP Server 的现代化改造之旅

在之前的博客中，我们分享了如何通过 FastAPI 包装器来解决 MCP Server 的鉴权和路径重写问题。然而，随着项目的发展，我们发现传统的 **SSE (Server-Sent Events)** 模式在复杂的云原生网络环境（GCP LB + Envoy）中显得越来越力不从心。

今天，我们将分享一次重大的架构升级：**迁移到 Streamable HTTP 模式**。

---

## 为什么要迁移？SSE 的阿喀琉斯之踵

SSE (Server-Sent Events) 是 MCP 协议早期的默认传输方式。它通过一个 GET 长连接接收事件，再通过 POST 请求发送指令。

**痛点 1：复杂的路径依赖**
SSE 模式下，Server 需要告诉 Client 一个“回调地址” (`endpoint`)。如果 Server 躲在层层代理（Envoy, Nginx）后面，它很难知道自己对外的真实 URL 是什么。我们之前为了解决这个问题，不得不引入了复杂的 `root_path` 和 `mount` 逻辑，结果还是在 URL 拼接上栽了跟头。

**痛点 2：长连接的脆弱性**
负载均衡器（Load Balancer）通常不喜欢长连接。如果没有心跳包，或者网络稍有波动，连接就会断开。

## 什么是 Streamable HTTP？

**Streamable HTTP** (JSON-RPC over HTTP) 是 MCP 协议的现代化传输方式。

*   **单一连接**：所有的通信（请求和响应）都通过标准的 HTTP POST 请求完成。
*   **无状态**：不需要维护一个长连接，每个请求都是独立的（虽然为了性能可以复用 TCP 连接）。
*   **简单**：Client 只需要知道一个 URL (e.g., `/mcp`)，不需要 Server 返回回调地址。

这简直就是为无服务器架构（Serverless, 如 Cloud Run）量身定做的！

---

## 代码改造：做减法

我们的迁移策略不是增加代码，而是**删除代码**。我们废弃了复杂的 FastAPI 包装层，回归 FastMCP 原生支持。

### 1. 升级 FastMCP
Streamable HTTP 是新特性，首先要确保依赖包是最新的。
```text
fastmcp>=2.14.3
```

### 2. Server 代码重构 (`mcp_github_tool_server.py`)

我们移除了 FastAPI，直接使用 `fastmcp` 启动。

**旧代码 (FastAPI Wrapper)**:
```python
app = FastAPI()
mcp_app = mcp.sse_app()
app.mount("/mcp", mcp_app)
# ... 还有复杂的 Middleware 和 uvicorn 启动逻辑
```

**新代码 (Streamable HTTP)**:
```python
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

# 定义鉴权中间件 (依然可以使用!)
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request.headers.get("X-Github-Token")
        if token:
            user_token_ctx.set(token)
        return await call_next(request)

if __name__ == "__main__":
    # 直接使用 mcp.run，指定 transport="http"
    mcp.run(
        transport="http", 
        host="0.0.0.0", 
        port=8000, 
        middleware=[Middleware(AuthMiddleware)],
        # 关键：指定监听路径，匹配 Envoy 的转发规则
        path="/mcp-github-tools-svc/mcp"
    )
```

### 3. Client 测试代码更新 (`test_client.py`)

客户端也需要切换到 HTTP 传输层。

```python
from fastmcp.client.transports import StreamableHttpTransport # 注意这里不是 SSETransport 了

# URL 直接指向端点，不需要 /sse 后缀
url = "https://www.jpgcp.cloud/mcp-github-tools-svc/mcp"

transport = StreamableHttpTransport(
    url=url,
    headers={
        "X-Github-Token": "sk-xxxx" # Header 鉴权依然完美支持
    }
)
```

---

## 鉴权黑科技：Header 传递

迁移到 Streamable HTTP 后，我们最担心的就是鉴权功能会丢失。
好消息是：FastMCP 的 HTTP 模式底层依然是 Starlette，它允许我们在 `run()` 方法中注入 Middleware。

我们保留了 **ContextVars** 的设计，中间件从 Header 提取 Token，存入 ContextVar，Tool 函数再从 ContextVar 读取。

**效果**：
*   用户在 Cline 配置里填入 Token。
*   Token 随 HTTP 请求头发送。
*   Server 自动捕获并使用。
*   **全程无感，且并发安全。**

---

## 总结

通过这次迁移，我们获得了一个更简单、更健壮、更符合云原生理念的系统。

1.  **代码量减少了 50%**：删除了 `server.py`。
2.  **部署更自信**：不再担心 Envoy 的路径重写会导致回调 URL 错误。
3.  **兼容性更好**：HTTP 协议是互联网的通用语言，穿透任何防火墙和代理都不在话下。

如果你的 MCP Server 也要上云，**Streamable HTTP** 绝对是你的首选。
