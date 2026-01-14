# 迁移至 Streamable HTTP (JSON-RPC) 模式的开发计划

鉴于 SSE (Server-Sent Events) 模式在经过多层代理（GCP LB -> Envoy -> Cloud Run）时遇到的路径重写和长连接稳定性问题，我们决定迁移到更健壮、更现代的 **Streamable HTTP** 模式。

## 1. 核心目标
*   **废弃 SSE**：不再依赖长连接，不再需要处理 `/sse` 和 `/messages` 的复杂状态同步。
*   **单一接口**：使用标准的 HTTP POST 接口（通常是 `/mcp` 或 `/`）来处理所有 JSON-RPC 请求。
*   **简化架构**：移除为了处理 SSE 路由而引入的 FastAPI 包装层 (`server.py`)，直接运行 FastMCP。

---

## 2. 代码修改清单

### 2.1 删除 FastAPI 包装层
*   **文件**: `server.py`
*   **操作**: **删除该文件**。
*   **原因**: FastMCP 的 HTTP 模式自带了所需的 ASGI 适配，不需要额外的 FastAPI 中间件来修正路径（因为 HTTP 模式通常是无状态的，或者路径依赖较少）。我们将回归到由 `fastmcp` 直接接管流量的模式。

### 2.2 改造 MCP Server 入口
*   **文件**: `src/servers/mcp_github_tool_server.py`
*   **修改**:
    1.  **启动方式**: 将 `mcp.run_sse_async()` 改为 `mcp.run(transport="http", ...)`。
    2.  **鉴权逻辑调整**:
        *   由于移除了 FastAPI 中间件，原有的 `user_token_ctx` 和 `auth_middleware` 逻辑将失效。
        *   **新策略**: 我们将鉴权逻辑下沉到 Tool 内部，或者利用 FastMCP 提供的 `dependencies` 注入机制（如果支持）。
        *   **临时方案**: 在 Tool 内部直接从 `kwargs` 或全局 Context 中尝试获取 Token（需要查阅 FastMCP 文档确认 HTTP 模式下如何获取 Header）。如果不行，暂时回退到仅支持 Server 端 Token，或者要求用户在参数中显式传递 Token。

### 2.3 更新测试客户端
*   **文件**: `src/clients/test_client.py`
*   **修改**:
    *   将 Transport 从 `SSETransport` 切换为 `HTTPTransport` (或 FastMCP 对应的 HTTP 客户端类)。
    *   URL 更新为 HTTP 端点（例如 `http://localhost:8000/mcp`）。

---

## 3. 部署与配置调整

### 3.1 部署配置
*   **文件**: `Dockerfile`
*   **修改**: `CMD` 指令需要从 `python server.py` 改为 `fastmcp run src/servers/mcp_github_tool_server.py:mcp --transport http --port 8000 --host 0.0.0.0`。
    *   或者，如果我们保留 python 脚本启动的方式，则在 python 脚本中调用 `mcp.run(transport='http')`。

### 3.2 Envoy 配置
*   **文件**: `envoy-config` 项目中的路由配置。
*   **修改**:
    *   HTTP 模式是标准的 Request-Response，对超时不敏感。
    *   可以将 `timeout` 恢复为默认值（或者保留长超时也无妨）。
    *   **关键**: 路径匹配可能需要调整。如果 FastMCP HTTP 模式监听 `/mcp`，Envoy 需要正确转发。

### 3.3 Cline 配置
*   **操作**: 用户需要将连接模式从 `sse` 改为 `http` (Streamable)。

---

## 4. 执行步骤

1.  **创建分支**: `feature/streamable-http`。
2.  **代码重构**: 修改 `mcp_github_tool_server.py`，删除 `server.py`。
3.  **本地验证**: 使用 `curl` 或更新后的 `test_client.py` 在本地跑通。
4.  **云端部署**: 更新 Cloud Run。
5.  **链路验证**: 验证 Envoy -> Cloud Run 的通路。
