# GCP + Envoy + FastAPI + MCP 部署中的 URL 路由深度解析

本文档详细解析了一个被代理的 MCP 服务器的精确请求/响应流程，诊断了过去遇到的问题，并提出了最终可行的配置方案。

## 问题：神秘的 POST 请求 "404 Not Found"

我们观察到 `GET /.../sse` 请求能成功，但后续的 `POST /.../messages` 请求却会失败并返回 404。核心问题在于我们技术栈的每一层对 URL 路径的期望不一致。

---

## 最终可行的解决方案

该方案确保了应用层（FastAPI）能够感知到其对外服务的完整路径，从而能够生成正确的回调 URL。

### 1. Envoy 配置 (`configs/routes/06_...yaml`)

关键在于**不要**将路径前缀重写为根路径 `/`。相反，我们应该重写它以保留基础路径。

```yaml
- match:
    prefix: "/mcp-github-tools-svc"
  route:
    cluster: mcp_github_tools_svc_cluster
    # 关键变更：重写到基础路径，而不是 "/"
    prefix_rewrite: "/mcp-github-tools-svc"
```

### 2. FastAPI 配置 (`server.py`)

现在，应用程序在预期的完整路径上挂载 MCP 服务器。

```python
# 不需要 root_path
app = FastAPI()

# 在 Envoy 将发送的完整路径上挂载 MCP 应用
mcp_app = mcp.sse_app()
app.mount("/mcp-github-tools-svc/mcp", mcp_app)

# 中间件也必须检查完整路径
@app.middleware("http")
async def context_middleware(request: Request, call_next):
    if request.url.path.startswith("/mcp-github-tools-svc/mcp/sse"):
        # ...
```

### 3. Cline 配置

客户端配置保持不变，指向公网 URL。

```json
{
    "url": "https://www.jpgcp.cloud/mcp-github-tools-svc/mcp/sse",
    ...
}
```

---

## 带有修复的 URL 流程分步解析

让我们追踪一次完整的握手流程。

### 第一步：SSE 连接 (GET)

1.  **Cline 启动**:
    *   **动作**: 发送 `GET` 请求。
    *   **URL**: `https://www.jpgcp.cloud/mcp-github-tools-svc/mcp/sse`

2.  **GCP 负载均衡器接收**:
    *   **动作**: 根据主机规则转发请求。
    *   **URL**: `https://www.jpgcp.cloud/mcp-github-tools-svc/mcp/sse` (不变)

3.  **Envoy 虚拟机接收**:
    *   **动作**: 匹配 `prefix: "/mcp-github-tools-svc"`。应用 `prefix_rewrite: "/mcp-github-tools-svc"`。
    *   **发送到 Cloud Run 的 URL**: `https://[cloud-run-url]/mcp-github-tools-svc/mcp/sse`

4.  **Cloud Run 容器 (FastAPI) 接收**:
    *   **路径**: `/mcp-github-tools-svc/mcp/sse`
    *   **动作**: FastAPI 的路由完美匹配 `app.mount("/mcp-github-tools-svc/mcp", ...)`。
    *   **结果**: 请求被成功地交给了 `mcp_app`。

5.  **FastMCP 响应**:
    *   **动作**: `mcp_app` 看到它被挂载在 `/mcp-github-tools-svc/mcp`。它知道其内部的 `/messages` 路径需要一个前缀。
    *   **SSE `endpoint` 事件**: `data: /mcp-github-tools-svc/mcp/messages/?session_id=...`
    *   **结果**: 成功 (200 OK)。

### 第二步：工具调用 (POST)

1.  **Cline 接收 `endpoint`**:
    *   **动作**: 它看到了**绝对路径** `/mcp-github-tools-svc/mcp/messages/...`，并且确切地知道如何构造下一个 URL。
    *   **POST 请求的 URL**: `https://www.jpgcp.cloud` + `/mcp-github-tools-svc/mcp/messages/?session_id=...`

2.  **Envoy & Cloud Run**:
    *   流程与第一步相同。完整路径被保留下来，并被 FastAPI 正确地路由到挂载的 `mcp_app`。

**这就创建了一个完美的、无歧义的请求生命周期，其中每个组件都对 URL 结构达成了一致。**
