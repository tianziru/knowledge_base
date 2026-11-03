# 灵犀智库

面向设备 / 产品说明书场景的智能问答系统：导入手册到知识库，按商品/设备名检索并生成可溯源回答。

| 端 | 端口 | 职责 |
|----|------|------|
| 导入后台 | `8000` | 文档上传、解析、切分、向量化、入库 |
| 问答前台 | `8001` | 多轮对话、商品确认、检索融合、答案生成 |

更细的背景与架构见 `docs/项目背景.md`、`docs/技术架构.md`。

---

## 环境要求

- Conda 环境：`knowledge_base`（Python 3.12）
- 已配置项目根目录下的 `.env`（大模型、BGE-M3、Milvus、MongoDB、MinIO 等）
- 依赖的外部服务按 `.env` 中地址可用（至少 Milvus、MongoDB）
- Redis 可选：未配置 `REDIS_URL` 时任务走 SQLite，SSE 走本进程队列

---

## 启动步骤

在项目根目录执行：

```bash
cd /Users/tianziru/Documents/project/knowledge_base
conda activate knowledge_base
```

### 1. 启动导入服务（8000）

```bash
python -m app.import_process.api.file_import_service
```

- 页面：http://127.0.0.1:8000/
- API 文档：http://127.0.0.1:8000/docs

### 2. 启动查询服务（8001）

另开一个终端，同样先激活环境：

```bash
cd /Users/tianziru/Documents/project/knowledge_base
conda activate knowledge_base
python -m app.query_process.api.query_service
```

- 页面：http://127.0.0.1:8001/
- API 文档：http://127.0.0.1:8001/docs

---

## 常用检查

```bash
# 确认环境
conda activate knowledge_base
which python   # 应指向 .../envs/knowledge_base/bin/python

# 确认端口是否已监听
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:8001 -sTCP:LISTEN
```

若端口已被占用，说明对应服务可能已在运行，可直接访问上述页面，无需重复启动。

---

## 配置说明

配置集中在根目录 `.env`，主要包括：

- 大模型：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`LLM_DEFAULT_MODEL`
- 向量模型：`BGE_M3_PATH`、`BGE_DEVICE`、`BGE_FP16`
- Milvus：`MILVUS_URL`、`CHUNKS_COLLECTION`、`ITEM_NAME_COLLECTION`
- MongoDB / MinIO / MinerU 等其它项
- 任务 / SSE（可选 Redis）：见下表

| 变量 | 默认 | 含义 |
|------|------|------|
| `REDIS_URL` | 空 | 非空且连接成功时启用 Redis（任务状态 + SSE Pub/Sub）；空则 SQLite + 本地队列 |
| `REDIS_KEY_PREFIX` | `kb` | Redis key / channel 前缀 |
| `TASK_LEASE_TTL_SEC` | `30` | Redis 下进行中任务的租约 TTL（秒） |
| `REDIS_REQUIRED` | `0` | `1` 时 Redis 连接失败则启动失败；默认回退 SQLite |

本机 Redis 示例：`REDIS_URL=redis://127.0.0.1:6379/0`（不要把真实密码写进仓库）。

修改 `.env` 后需**重启**对应服务进程才会生效。

---

## 超长 PDF

MinerU 云端单文件约有 **200 页**上限。导入时若页数超过 `MINERU_MAX_PAGES`（默认 180），会在 `node_pdf_to_md` 内自动按页拆分、有限并行解析、再合并为一份 MD（含图片去重命名），下游节点无感。

| 变量 | 默认 | 含义 |
|------|------|------|
| `MINERU_MAX_PAGES` | `180` | 单段最大页数（实现会 clamp 到 ≤200） |
| `MINERU_SPLIT_CONCURRENCY` | `2` | 同时处理的分段数 |
| `MINERU_PART_RETRIES` | `2` | 单段失败后的额外重试；仍失败则整单失败 |

修改 `.env` 后需重启导入服务（8000）。

---

## 说明

- 依赖由 Conda 环境 `knowledge_base` 管理，不使用 `pyproject.toml` / `uv`。
- 两个服务为**独立进程**，需分别启动。
- 任务状态默认写入 SQLite（`data/tasks.db`）；配置 `REDIS_URL` 后改用 Redis，供多实例共享任务进度与 SSE。
- 本机 Redis 示例：`docker run -d --name kb-redis -p 6379:6379 redis:7-alpine`
- 相关变量：`REDIS_URL`、`REDIS_KEY_PREFIX`（默认 `kb`）、`TASK_LEASE_TTL_SEC`（默认 `30`）、`REDIS_REQUIRED`（默认 `0`）
