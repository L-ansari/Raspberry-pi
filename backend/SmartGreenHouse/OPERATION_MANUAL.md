# 智能温室后端系统 · 操作说明

## 1. 系统概述

本项目是「智能温室」的**后端服务**，采用 Django + Django REST Framework，数据存储在 **MongoDB**
（通过 `django-mongodb-backend`）。它负责：

- 采集并存储温室传感器读数（温度、湿度、土壤湿度、光照）；
- 查询历史读数、按时间范围或 ID 删除；
- 用户注册与 JWT 登录认证；
- 管理多个**边缘节点**（如各温室区域的树莓派）：注册、心跳存活监测、离线检测；
- 把传感器读数与来源节点/区域关联；
- 通过 Ollama 本地大模型生成种植建议和对话回复。

> 边缘节点只负责采集和上报数据，**所有数据处理、分析、异常检测、AI 建议都在中央后端完成**。

---

## 2. 环境要求与安装

| 依赖 | 说明 |
|---|---|
| Python | 3.10+（本项目在 Python 3.14 上验证过安装） |
| MongoDB | 本地或 MongoDB Atlas（已有 `atlas-credentials.env` 里的连接串） |
| Django | **≥ 5.2**（`django-mongodb-backend` 5.2.x 的要求；4.2 不兼容） |
| 其他包 | djangorestframework、djangorestframework-simplejwt、django-mongodb-backend、python-dotenv、requests、pymongo、dnspython |

建议用隔离环境安装：

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install "Django>=5.2,<6.0" "django-mongodb-backend==5.2.4" djangorestframework djangorestframework-simplejwt python-dotenv requests pymongo dnspython
```

> ⚠️ 注意：本机若已装 Django 4.2.5，需用隔离环境升级到 5.2；否则 `django-mongodb-backend` 无法安装、项目无法运行。

---

## 3. 配置说明

### 3.1 MongoDB

在项目根目录的 `atlas-credentials.env` 中配置（默认已存在）：

```dotenv
MONGODB_URI=mongodb+srv://...
MONGODB_DB=greenhouse
```

### 3.2 边缘节点（可选，有默认值）

```dotenv
EDGE_PROVISIONING_TOKEN=my-secret-token      # 设备注册用的共享密钥；为空则禁用 token 注册
EDGE_HEARTBEAT_TIMEOUT=60                     # 心跳超时秒数，超过则判为离线
EDGE_ALLOWED_ZONES=zone-1,zone-2,zone-3       # 允许分配的区域白名单（逗号分隔）
```

### 3.3 Ollama（LLM 功能，需手动补）

`llm/services.py` 需要 `OLLAMA_BASE_URL` 和 `OLLAMA_MODEL`，但 `settings.py` **当前未定义**。使用 AI 建议/对话前，在 `settings.py` 里补：

```python
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
```

并确保本机 Ollama 已启动、模型已 `ollama pull`。

---

## 4. 数据库迁移

首次部署需执行迁移（生成集合）：

```powershell
python manage.py makemigrations api
python manage.py migrate
```

**如果 MongoDB 里已有旧集合**（如 `auth_user`、`api_sensorreading`），直接 `migrate` 会报
`CollectionInvalid: collection ... already exists`。此时用 `--fake` 只记录迁移、不重建集合：

```powershell
python manage.py migrate --fake
```

MongoDB 无 schema：`SensorReading` 新增的 `node_id`/`zone_id` 对旧文档透明（读到为 `null`）；
新的 `edge_node` 集合会在第一次注册节点时自动创建。

---

## 5. 启动与停止

启动开发服务器：

```powershell
python manage.py runserver
```

默认地址 `http://127.0.0.1:8000`，API 前缀为 `/api/`。按 `Ctrl+C` 停止。

---

## 6. 用户与登录

1. **注册**：`POST /api/users/register/`，Body `{username, email, password}`（密码 ≥ 8 位）。
2. **登录**：`POST /api/users/login/`，Body `{username, password}`，得到 `access` 和 `refresh`。
3. 之后访问需要登录的接口，Header 加 `Authorization: Bearer <access-token>`。
4. access 过期后，用 `POST /api/users/token/refresh/` + `{refresh}` 换新 access。

---

## 7. 传感器数据管理

| 操作 | 方法 + 路径 |
|---|---|
| 健康检查 | `GET /api/health_check/` |
| 上传读数 | `POST /api/sensors/` |
| 读全部 | `GET /api/sensors/` |
| 读单个 | `GET /api/sensors/<id>/` |
| 读历史（1h/24h/7d/30d） | `GET /api/sensors/history/<range>/` |
| 按 ID 删除 | `DELETE /api/sensors/del/<id>/` |
| 按范围删除 | `DELETE /api/sensors/history/del/<range>/` |

> ⚠️ **权限**：读全部/读单个/读历史/删除 四个接口都需要登录（Header 带 `Authorization: Bearer <access-token>`），且只能操作「自己拥有节点」产生的数据；超管可见全部。**上传读数无需登录**（保留 legacy / 设备 key 上报）。

上传读数示例（legacy，无凭据）：

```json
{ "temperature": 24.5, "humidity": 58.2, "soil_moisture": 42.7, "light": 760 }
```

- 老客户端**不传任何认证头**照常工作，读数不带节点/区域（`node_id`/`zone_id` 为 `null`）。
- 边缘设备上传时加 `X-Edge-Key`，后端自动把读数关联到该节点及其区域（**以 key 为准，不信任客户端传的 node_id/zone_id**）。

---

## 8. 边缘节点管理

### 8.1 注册节点（二选一授权）

**方式 A：共享 provisioning token**

```http
POST /api/edges/register/
Content-Type: application/json
```
```json
{
  "node_id": "pi-zone-1",
  "name": "Raspberry Pi Zone 1",
  "zone_id": "zone-1",
  "provisioning_token": "my-secret-token"
}
```

**方式 B：管理员 JWT**（带 `Authorization: Bearer <access-token>`，body 不传 provisioning_token）。

- **归属规则**：方式 B（JWT）注册时，登录用户自动成为该节点 `owner`；方式 A（provisioning token）注册的节点 `owner` 为空（无主，仅超管可见）。
- 注册成功返回一次性 `api_key`，**务必立即保存**（服务端只存哈希，之后无法再取回）。

### 8.2 心跳

设备周期性调用（与上传数据无关）：

```http
POST /api/edges/heartbeat/
X-Edge-Key: <api-key>
```

成功即把节点标记为 `online` 并刷新 `last_heartbeat`。

### 8.3 查看节点

`GET /api/edges/`（需用户 JWT），返回**当前用户拥有**的节点及状态（含 `owner` 字段，不含任何密钥）；超管返回全部节点（含无主节点）。

### 8.4 离线检测

心跳超时（默认 60 秒）的节点，由命令标记为离线：

```powershell
python manage.py check_edge_health
```

该命令**不会自动定时执行**，需用系统调度器周期性运行，例如 cron / 计划任务：

```cron
* * * * * cd /path/to/SmartGreenHouse && /path/to/python manage.py check_edge_health
```

### 8.5 设备吊销

把节点 `status` 改为 `disabled`（或删除该节点），其 API key 即失效，心跳和上报都会被拒绝。

### 8.6 数据归属与权限（Ownership）

- **节点归属**：每个 `EdgeNode` 有一个 `owner`（单用户外键）。JWT 注册 → owner=该用户；provisioning token 注册 → owner 为空（无主）。
- **数据隔离**：传感器读数通过 `node_id` 归属到节点，再归属到 owner。用户只能读/删「自己拥有节点」产生的读数；超管可见全部。
- **无主数据**：`node_id` 为空的 legacy/匿名读数是无主数据，仅超管可见。
- **跨用户访问**：读/删他人数据一律返回 `404`（不泄露对象是否存在）。
- **节点列表**：非超管只返回自己的节点；超管返回全部。
- **删除用户**：不级联删除节点，`owner` 置空（节点变无主、仅超管可见），避免误删设备与数据。
- **LLM**：建议/对话接口也需登录，且只基于当前用户自己的读数生成内容，避免经 AI 间接泄露他人数据。

---

## 9. AI 建议与对话（LLM）

| 操作 | 方法 + 路径 | 说明 |
|---|---|---|
| 种植建议 | `POST /api/llm/recommend/` | Body `{hours, language}` |
| 对话 | `POST /api/llm/chat/` | Body `{message, language}` |

- **需登录**（`Authorization: Bearer <access-token>`），且只基于当前用户自己的读数生成内容。
- 依赖 Ollama（见 3.3）。
- 若 Ollama 不可用/返回异常，返回 `503`。
- 语言参数接受 `en`/`zh`；当前 `zh` 被映射为瑞典语（已知问题）。

---

## 10. 常见问题与注意事项

1. **迁移报 `collection already exists`** → 用 `python manage.py migrate --fake`（见第 4 节）。
2. **LLM 接口 500/报错** → 检查是否补了 `OLLAMA_BASE_URL`/`OLLAMA_MODEL`，以及 Ollama 是否启动。
3. **注册节点 401** → 检查 `EDGE_PROVISIONING_TOKEN` 是否已配置并重启；或改用管理员 JWT 注册。
4. **注册节点 400 zone 校验失败** → `zone_id` 必须在 `EDGE_ALLOWED_ZONES` 白名单内。
5. **安全提醒**：`settings.py` 目前 `DEBUG=True`、`SECRET_KEY` 硬编码、`ALLOWED_HOSTS=["*"]`，仅供开发，**切勿部署到生产**；生产请改用环境变量注入密钥、关闭 DEBUG、收紧 ALLOWED_HOSTS，并按 Django 部署清单配置 HTTPS。
6. **不要提交密钥**：`atlas-credentials.env`、设备 api_key、provisioning token 都不要提交到代码库。

---

## 11. 已知限制

- `DELETE /api/sensors/history/del/<range>/` 对非法 range 未显式返回错误状态码（可能仍 `200`，响应体含 `error`）。
- LLM 语言参数 `zh` 被映射为瑞典语，非中文。
- LLM 所需 `OLLAMA_*` 配置在 `settings.py` 中缺失（需自行补上）。
- **django-mongodb-backend 兼容性**：Django 的 `create_permissions`（post_migrate）依赖自增主键语义，在全新数据库或新建 ContentType 时会崩溃（`TypeError: Model instances without primary key value are unhashable`）。本项目已在 `users/apps.py` 中**断开该 receiver** 作为变通：本项目不使用 Django 的 `Permission` 模型（认证走 JWT、授权走节点归属），因此功能无损；ContentType 仍会正常创建。若未来需要 Django 权限系统，需改用支持该语义的数据库后端或自行实现权限同步。

完整接口契约与细节见 `frontend-api.md`；完整测试用例见 `TEST_CASES.md`。
