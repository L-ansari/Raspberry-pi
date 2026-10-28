# 智能温室后端 · 系统测试用例（API + JSON + 预期返回）

本文件覆盖**现有全部功能**的接口测试用例：健康检查、传感器读数、用户认证、LLM、边缘节点管理，以及离线检测命令。

## 约定

- 基础地址：`baseUrl = http://127.0.0.1:8000`
- 动态值用 `<...>` 占位表示（如 `<access-token>`、`<ObjectId>`、`<api-key>`、时间戳等），实际返回以服务端生成为准。
- 所有请求体均为 `raw JSON`，Header 需要 `Content-Type: application/json`（下面不再逐条重复）。
- 建议**按编号顺序执行**，因为部分用例有依赖（先注册用户 → 登录 → 注册节点）。
- **权限模型**：传感器读/删、节点列表、LLM 接口都需要 `Authorization: Bearer <access-token>`；用户只能读/删「自己拥有节点」产生的数据，超管可见全部（含无主数据）；跨用户访问返回 `404`。传感器**上传**无需登录（保留 legacy / 设备 key）。
- 环境变量（测试前先配好，见操作说明）：
  - `EDGE_PROVISIONING_TOKEN=my-secret-token`
  - `EDGE_ALLOWED_ZONES=zone-1,zone-2,zone-3`
  - `EDGE_HEARTBEAT_TIMEOUT=60`

---

## 1. 健康检查

### TC-01 后端健康检查
- **GET** `/api/health_check/`
- 请求体：无
- 预期：`200 OK`
```json
{ "status": "ok", "message": "Greenhouse backend is running" }
```

---

## 2. 传感器读数（Sensor Reading）

传感器字段：`temperature`(温度)、`humidity`(湿度)、`soil_moisture`(土壤湿度)、`light`(光照) 为必填数字；`id`/`timestamp`/`node_id`/`zone_id` 由后端生成。

### TC-02 读取全部读数（空）
- **GET** `/api/sensors/`
- Header：`Authorization: Bearer <access-token>`（需登录）
- 预期：`200 OK`
```json
[]
```
- 未登录时预期 `401`（见 TC-40）。

### TC-03 创建读数（无凭据，legacy 客户端）
- **POST** `/api/sensors/`
- 请求体：
```json
{ "temperature": 24.5, "humidity": 58.2, "soil_moisture": 42.7, "light": 760 }
```
- 预期：`201 Created`，`node_id`/`zone_id` 为 `null`
```json
{
  "id": "<ObjectId>",
  "temperature": 24.5,
  "humidity": 58.2,
  "soil_moisture": 42.7,
  "light": 760,
  "timestamp": "2026-10-28T12:00:00Z",
  "node_id": null,
  "zone_id": null
}
```

### TC-04 创建读数（带设备 key，自动关联节点/区域）
- **POST** `/api/sensors/`
- Header：`X-Edge-Key: <api-key>`（由 TC-29 注册节点获得）
- 请求体：
```json
{ "temperature": 26.3, "humidity": 61.0, "soil_moisture": 40.5, "light": 820 }
```
- 预期：`201 Created`，`node_id`/`zone_id` 由后端从 key 派生（不是客户端传的）
```json
{
  "id": "<ObjectId>",
  "temperature": 26.3,
  "humidity": 61.0,
  "soil_moisture": 40.5,
  "light": 820,
  "timestamp": "2026-10-28T12:01:00Z",
  "node_id": "pi-zone-1",
  "zone_id": "zone-1"
}
```

### TC-05 创建读数（非法/缺字段）
- **POST** `/api/sensors/`
- 请求体：`{ "temperature": "不是数字" }`
- 预期：`400 Bad Request`（DRF 默认错误格式）
```json
{
  "humidity": ["This field is required."],
  "soil_moisture": ["This field is required."],
  "light": ["This field is required."],
  "temperature": ["A valid number is required."]
}
```

### TC-06 读取单个读数（存在）
- **GET** `/api/sensors/<ObjectId>/`
- Header：`Authorization: Bearer <access-token>`
- 预期：`200 OK`，返回单个读数对象（结构同 TC-03）；非归属/无主数据返回 `404`

### TC-07 读取单个读数（非法 ID）
- **GET** `/api/sensors/not-an-objectid/`
- 预期：`400 Bad Request`
```json
{ "error": "Invalid sensor ID" }
```

### TC-08 读取单个读数（不存在）
- **GET** `/api/sensors/000000000000000000000000/`
- 预期：`404 Not Found`
```json
{ "error": "Sensor reading not found" }
```

### TC-09 按时间范围查历史（24h）
- **GET** `/api/sensors/history/24h/`
- Header：`Authorization: Bearer <access-token>`
- 预期：`200 OK`，返回旧→新的读数数组 `[ {...}, ... ]`（仅本人归属数据）
- 支持范围：`1h` / `24h` / `7d` / `30d`

### TC-10 非法时间范围
- **GET** `/api/sensors/history/xxx/`
- 预期：`400 Bad Request`
```json
{ "error": "Invalid range", "allowed_values": ["1h", "24h", "7d", "30d"] }
```

### TC-11 按 ID 删除单个读数
- **DELETE** `/api/sensors/del/<ObjectId>/`
- Header：`Authorization: Bearer <access-token>`
- 预期：`200 OK`，返回被删除的读数对象；非归属返回 `404`

### TC-12 按时间范围删除读数
- **DELETE** `/api/sensors/history/del/24h/`
- Header：`Authorization: Bearer <access-token>`
- 预期：`200 OK`，返回被删除的读数数组 `[ {...}, ... ]`（仅删除本人归属数据）

### TC-13 删除-非法时间范围（已知 bug）
- **DELETE** `/api/sensors/history/del/xxx/`
- 预期：状态码可能仍是 `200`（未显式赋错误码），响应体含 error
```json
{ "error": "Invalid range", "allowed_values": ["1h", "24h", "7d", "30d"] }
```

### TC-14 删除-非法/不存在 ID（已知 bug）
- **DELETE** `/api/sensors/del/<不存在的ObjectId>/`
- 预期：**行为不一致**（可能 400/500 或非预期），当前实现未正确处理非法/不存在 ID，测试时不要依赖固定状态码。

---

## 3. 用户与认证（Users / JWT）

### TC-15 注册用户（成功）
- **POST** `/api/users/register/`
- 请求体：
```json
{ "username": "admin", "email": "admin@example.com", "password": "secret-pass-123" }
```
- 预期：`201 Created`
```json
{
  "message": "User registered successfully.",
  "user": {
    "id": "<user-id>",
    "username": "admin",
    "email": "admin@example.com",
    "first_name": "",
    "last_name": "",
    "date_joined": "2026-10-28T12:00:00Z"
  }
}
```

### TC-16 注册用户（密码太短）
- **POST** `/api/users/register/`
- 请求体：`{ "username": "u2", "email": "u2@example.com", "password": "123" }`
- 预期：`400 Bad Request`
```json
{ "errors": { "password": ["Ensure this field has at least 8 characters."] } }
```

### TC-17 注册用户（缺字段）
- **POST** `/api/users/register/`
- 请求体：`{ "username": "u3" }`
- 预期：`400 Bad Request`
```json
{ "errors": { "email": ["This field is required."], "password": ["This field is required."] } }
```

### TC-18 登录获取 JWT（成功）
- **POST** `/api/users/login/`
- 请求体：`{ "username": "admin", "password": "secret-pass-123" }`
- 预期：`200 OK`，复制 `access` 到 `<access-token>`
```json
{ "refresh": "<refresh-token>", "access": "<access-token>" }
```

### TC-19 登录（密码错误）
- **POST** `/api/users/login/`
- 请求体：`{ "username": "admin", "password": "wrong-password" }`
- 预期：`401 Unauthorized`
```json
{ "detail": "No active account found with the given credentials" }
```

### TC-20 刷新 Access Token
- **POST** `/api/users/token/refresh/`
- 请求体：`{ "refresh": "<refresh-token>" }`
- 预期：`200 OK`
```json
{ "access": "<new-access-token>" }
```

### TC-21 获取当前用户（带 token）
- **GET** `/api/users/me/`
- Header：`Authorization: Bearer <access-token>`
- 预期：`200 OK`
```json
{
  "id": "<user-id>",
  "username": "admin",
  "email": "admin@example.com",
  "first_name": "",
  "last_name": "",
  "date_joined": "2026-10-28T12:00:00Z"
}
```

### TC-22 获取当前用户（不带 token）
- **GET** `/api/users/me/`（无 Authorization）
- 预期：`401 Unauthorized`（或 `403`）。该接口现已显式要求登录。

---

## 4. LLM 功能（AI 建议 / 对话）

> ⚠️ **前置**：LLM 端点依赖 `settings.OLLAMA_BASE_URL` 和 `settings.OLLAMA_MODEL`，但当前 `settings.py` **尚未定义这两个配置**。测试前需先在 `settings.py`（或环境变量）里补上，并确保本地 Ollama 服务已启动、模型已拉取；否则接口会报错（目前是配置缺失导致的 `500`，而非文档中的 `503`）。

### TC-23 生成种植建议（成功）
- **POST** `/api/llm/recommend/`
- 请求体：
```json
{ "hours": 24, "language": "en" }
```
- 预期：`200 OK`
```json
{
  "status": "success",
  "recommendation": "The latest reading shows ...",
  "context": {
    "latest_reading": { "...": "..." },
    "history_hours": 24,
    "historical_readings": []
  },
  "generated_at": "2026-10-28T12:10:00Z"
}
```

### TC-24 建议-参数校验失败
- **POST** `/api/llm/recommend/`
- 请求体：`{ "hours": 9999 }`
- 预期：`400 Bad Request`
```json
{ "errors": { "hours": ["Ensure this value is less than or equal to 720."] } }
```

### TC-25 建议-Ollama 不可用
- **POST** `/api/llm/recommend/`（Ollama 未启动或模型不存在时）
- 预期：`503 Service Unavailable`
```json
{ "error": "Could not communicate with Ollama. Check that Ollama is running and the model is available." }
```

### TC-26 对话（成功）
- **POST** `/api/llm/chat/`
- 请求体：
```json
{ "message": "What do the latest sensor readings suggest?", "language": "en" }
```
- 预期：`200 OK`
```json
{
  "status": "success",
  "reply": "Based on the available readings ...",
  "context_used": { "latest_reading": true, "historical_readings": true },
  "generated_at": "2026-10-28T12:10:00Z"
}
```

### TC-27 对话-空消息
- **POST** `/api/llm/chat/`
- 请求体：`{ "message": "" }`
- 预期：`400 Bad Request`
```json
{ "errors": { "message": ["This field may not be blank."] } }
```

### TC-28 语言映射（已知 bug）
- 传 `language: "zh"` 期望中文，但当前实现 `zh` 被映射为**瑞典语**，测试时以实际返回为准。

---

## 5. 边缘节点管理（Edge Nodes）

### TC-29 注册节点（provisioning token 方式）
- **POST** `/api/edges/register/`
- 请求体：
```json
{
  "node_id": "pi-zone-1",
  "name": "Raspberry Pi Zone 1",
  "zone_id": "zone-1",
  "provisioning_token": "my-secret-token"
}
```
- 预期：`201 Created`，**`api_key` 只返回这一次**，复制到 `<api-key>`
```json
{
  "message": "Edge node registered successfully.",
  "node": {
    "node_id": "pi-zone-1",
    "name": "Raspberry Pi Zone 1",
    "zone_id": "zone-1",
    "status": "offline",
    "owner": null,
    "ip_address": null,
    "last_heartbeat": null,
    "last_data_at": null,
    "created_at": "2026-10-28T12:00:00Z",
    "updated_at": "2026-10-28T12:00:00Z"
  },
  "api_key": "<api-key>"
}
```

### TC-30 注册节点（JWT 方式，管理员）
- **POST** `/api/edges/register/`
- Header：`Authorization: Bearer <access-token>`
- 请求体（不带 provisioning_token）：
```json
{ "node_id": "pi-zone-2", "name": "Raspberry Pi Zone 2", "zone_id": "zone-2" }
```
- 预期：`201 Created`，返回 `node` + `api_key`，且 `node.owner == "<用户名>"`（JWT 用户自动成为 owner）

### TC-31 注册节点（重复 node_id）
- **POST** `/api/edges/register/`（再用一次 `node_id: "pi-zone-1"`）
- 预期：`409 Conflict`
```json
{ "error": "A node with this node_id is already registered." }
```

### TC-32 注册节点（非法区域）
- **POST** `/api/edges/register/`
- 请求体：`{ "node_id": "pi-x", "name": "X", "zone_id": "zone-999", "provisioning_token": "my-secret-token" }`
- 预期：`400 Bad Request`
```json
{ "errors": { "zone_id": ["Zone 'zone-999' is not permitted. Allowed zones: zone-1, zone-2, zone-3"] } }
```

### TC-33 注册节点（未授权）
- **POST** `/api/edges/register/`（不带 token、不带 JWT）
- 预期：`401 Unauthorized`
```json
{ "error": "Provisioning token or authentication required." }
```

### TC-34 心跳（成功）
- **POST** `/api/edges/heartbeat/`
- Header：`X-Edge-Key: <api-key>`（body 可留空）
- 预期：`200 OK`，节点变 `online`
```json
{ "status": "online", "node_id": "pi-zone-1", "last_heartbeat": "2026-10-28T12:05:00Z" }
```

### TC-35 心跳（错误 key）
- **POST** `/api/edges/heartbeat/`
- Header：`X-Edge-Key: wrong-key`
- 预期：`401 Unauthorized`
```json
{ "detail": "Invalid edge API key." }
```

### TC-36 心跳（禁用节点）
- 先把该节点 `status` 改为 `disabled`（可用 Django shell 或数据库），再用其 key 发心跳
- 预期：`401 Unauthorized`
```json
{ "detail": "Edge node is disabled." }
```

### TC-37 节点列表（未认证）
- **GET** `/api/edges/`
- 预期：`401 Unauthorized` 或 `403 Forbidden`

### TC-38 节点列表（已认证）
- **GET** `/api/edges/`
- Header：`Authorization: Bearer <access-token>`
- 预期：`200 OK`，仅返回**本人拥有**的节点（超管返回全部），数组**不含** `api_key`/`api_key_hash`
```json
[
  {
    "node_id": "pi-zone-1",
    "name": "Raspberry Pi Zone 1",
    "zone_id": "zone-1",
    "status": "online",
    "owner": "admin",
    "ip_address": "127.0.0.1",
    "last_heartbeat": "2026-10-28T12:05:00Z",
    "last_data_at": "2026-10-28T12:01:00Z",
    "created_at": "2026-10-28T12:00:00Z",
    "updated_at": "2026-10-28T12:05:00Z"
  }
]
```

---

## 6. 离线检测命令（终端，非 API）

### TC-39 离线检测
在终端执行：
```powershell
python manage.py check_edge_health
```
预期行为：
- 心跳新鲜（60 秒内）的节点保持 `online`；
- 心跳超时或缺失的 `online` 节点变为 `offline`；
- `disabled` 节点保持不变；
- 重复执行安全（幂等），已 `offline` 的不会被改写。

---

## 7. 数据归属与权限隔离（Ownership）

> 前置：注册两个普通用户 `alice` / `bob`，各自用 JWT 注册自己的节点并上报读数；另注册一个 superuser `root`。
> 用 `<alice-token>`、`<bob-token>`、`<root-token>` 分别代表其 access token。

### TC-40 传感器读接口未登录
- 依次对 `/api/sensors/`、`/api/sensors/<id>/`、`/api/sensors/history/24h/`、`/api/sensors/del/<id>/` 发 GET/DELETE，**不带** Authorization
- 预期：均为 `401 Unauthorized`（上传 `POST /api/sensors/` 仍无需登录，保持兼容）

### TC-41 节点列表只返回本人拥有
- **GET** `/api/edges/`，`Authorization: Bearer <bob-token>`
- 预期：`200 OK`，只含 bob 自己注册的节点，**不含** alice 的节点；节点含 `owner` 字段

### TC-42 读不到他人读数
- **GET** `/api/sensors/<alice的读数id>/`，`Authorization: Bearer <bob-token>`
- 预期：`404 Not Found`（不泄露该读数是否存在）
- **GET** `/api/sensors/`、`/api/sensors/history/24h/`（bob）
- 预期：`200 OK`，结果里**不含** alice 的读数

### TC-43 删不到他人读数
- **DELETE** `/api/sensors/del/<alice的读数id>/`，`Authorization: Bearer <bob-token>`
- 预期：`404 Not Found`，alice 的读数**仍存在**（未被删除）

### TC-44 无主数据仅超管可见
- 用「无凭据」POST 一条 legacy 读数（`node_id`/`zone_id` 为 `null`）
- **GET** `/api/sensors/`（bob）→ 结果**不含**该条（`200`，空数组或不含该 id）
- **GET** `/api/sensors/`（root）→ 结果**包含**该条（`200`）

### TC-45 超管可见全部
- **GET** `/api/edges/`（root）→ 返回 alice、bob 的节点 + 无主节点（若有用 provisioning token 注册的）
- **GET** `/api/sensors/`（root）→ 返回全部读数（含 legacy 无主数据）

### TC-46 LLM 接口需登录（未登录 401）
- **POST** `/api/llm/recommend/`、`/api/llm/chat/`（不带 Authorization）
- 预期：`401 Unauthorized`
- 已登录场景需先补 `OLLAMA_BASE_URL`/`OLLAMA_MODEL` 并启动 Ollama（见 TC-23~27），且只会基于当前用户自己的读数生成建议/回复。

---

## 建议的整体执行顺序

1. TC-01 健康检查
2. TC-15 → TC-18 → TC-21 用户注册/登录/当前用户
3. TC-29 注册节点（拿到 `<api-key>`）
4. TC-34 心跳（节点变 online）
5. TC-04 带 key 上报传感器（关联节点）
6. TC-03 无凭据上报传感器（legacy 对比）
7. TC-02 / TC-06 / TC-09 读接口
8. TC-38 节点列表
9. TC-11 / TC-12 删除接口
10. TC-39 离线检测
11. （可选）TC-23~27 LLM（需先补 OLLAMA 配置并启动 Ollama）
12. TC-40~45 归属与权限隔离（再注册 alice/bob/root 三个账号各测一遍）
13. TC-46 LLM 登录校验
