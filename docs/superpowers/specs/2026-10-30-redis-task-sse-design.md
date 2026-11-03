# 任务状态与 SSE 的 Redis 共享设计

**日期：** 2026-10-30  
**状态：** 已批准（用户确认：目标 B 多实例共享；可新起 Redis；任务+SSE；双后端回退 SQLite；方案 2）

## 背景与问题

任务状态已由 `task_utils` + `task_store`（SQLite `data/tasks.db`）写穿持久化：单进程重启后已完成任务可恢复，进行中任务在启动时标为 `failed`。进程内 dict 仍为热缓存。

多 worker / 多实例下存在两类问题：

1. **任务热缓存不共享**：各进程内存视图不一致；SQLite 写锁与「读仍走本机内存」无法保证跨实例一致。
2. **SSE 队列在进程内存**（`sse_utils._session_stream`）：请求落在 A、SSE 连在 B 时，进度与流式推送丢失。

README 仍写「任务进度在内存、重启丢失」，表述已过时，需随本期一并更正。

## 目标

- 配置 `REDIS_URL` 时：多实例共享同一份任务状态；SSE 跨进程可推送。
- 未配置或 Redis 不可用（默认）：回退现有 SQLite + 本地 SSE，行为与现网一致。
- `task_utils` / 对外 HTTP 与节点调用点尽量不变。

## 方案

**方案 2：Redis 为权威数据源 + 本地无任务热缓存 + Pub/Sub SSE（已选）**

未选：

- 方案 1：仅把 `task_store` 换成 Redis Hash、仍保留进程 dict（多实例易脏读；启动批量标 failed 会误杀他机任务）。
- 方案 3：完整任务总线 + 认领队列 + 插件化运维（本期过重）。

## 范围

### 做

1. 双后端：有 `REDIS_URL` → Redis（任务 + SSE）；否则 → SQLite + 本地 queue。
2. Redis 任务：Hash + ZSET 索引；字段与现 SQLite 行对齐，并增加 `owner`（worker_id）。
3. Redis 模式下去掉任务权威热缓存；读写直达 Redis。
4. 心跳租约（lease）：仅 Redis 模式；禁止启动时全局把 pending/processing 标 failed。
5. SSE：Redis Pub/Sub channel；`push_to_session` / `sse_generator` 走总线抽象。
6. 配置项、本机 Redis 启动说明、架构/README/项目背景文档更新。
7. 测试：SQLite 回归 + fakeredis 多 client 共享 + lease 过期 + SSE 跨「假 worker」。

### 不做

- 导入流水线断点续跑（resume）
- SQLite → Redis 自动迁库
- SSE 事件持久化 / 断线重放
- 将 `set_task_result` 的 `answer` 等非 `error` 字段写入 Redis（与现 SQLite 一致，仅持久 `error`）
- 对话历史（仍 MongoDB）
- K8s/生产 HA 专项编排（文档仅给本机 Docker 示例）

## 架构

```
┌─────────────┐  ┌─────────────┐
│ worker      │  │ worker      │
│ import/query│  │ …多实例     │
└──────┬──────┘  └──────┬──────┘
       │ task_utils / sse_utils API 不变
       ▼
┌──────────────────────────────┐
│ 启动时选择 backend           │
│ REDIS_URL 可用 → Redis       │
│ 否则 / 连接失败* → SQLite    │
└──────────────┬───────────────┘
               ▼
     Redis（可选）
  · Hash/ZSET：任务
  · Pub/Sub：SSE
  · String+TTL：lease
```

\* 默认回退 SQLite；`REDIS_REQUIRED=1` 时连接失败则启动失败。

**边界**

- 节点与 `file_import_service` / `query_service` 业务逻辑尽量不改。
- SQLite 模式：热缓存 + 写穿 + 启动将未结束任务标 failed（保持现行为）。
- Redis 模式：租约超时后将孤儿任务标 failed；他机任务不受本机启动影响。

## 数据模型（Redis）

前缀默认 `kb`（`REDIS_KEY_PREFIX` 可覆盖）。

| Key | 类型 | 内容 |
|-----|------|------|
| `{prefix}:task:{task_id}` | Hash | `status`、`file_name`、`file_size`、`created_at`、`updated_at`、`done_list`/`running_list`（JSON 字符串，原始节点 ID）、`error`、`owner` |
| `{prefix}:tasks:index` | ZSET | member=`task_id`，score=`created_at` epoch，列表按新到旧 |
| `{prefix}:task:{task_id}:lease` | String + TTL | 值=`worker_id`；仅 pending/processing |
| `{prefix}:sse:{session_id}` | Pub/Sub channel | 消息 JSON：`{"event": "...", "data": {...}}` |

与 SQLite 表字段对齐；`done_list`/`running_list` 存原始节点 ID（展示层仍由 `task_utils` 转中文）。

## 心跳租约（仅 Redis）

1. 进入 `pending`/`processing`：`SET {prefix}:task:{id}:lease {worker_id} EX {TASK_LEASE_TTL_SEC}`（默认 30）。
2. 持有任务的 worker 每约 `TTL/3` 续期；进度写穿时可顺带续期。
3. 检测以 **读路径懒检测为主**（`get_task_status` / `list_tasks` / `get_task_stats` 时检查 lease）；可选再加后台线程按分钟扫描，非必须。lease 不存在且 status 仍为 pending/processing → `failed`，`error=任务租约过期（worker 可能已退出）`，清空 `running_list`。
4. **禁止** 启动时批量标记全部进行中任务为 failed。
5. `completed`/`failed` 时删除 lease key。

每个进程启动时生成一次 `worker_id`（UUID4），写入 Hash `owner` 供观测；租约以 key 是否存在为准。不做基于 owner 的复杂抢占（YAGNI：单任务通常单执行方）。

## 组件与改造点

| 组件 | 职责 |
|------|------|
| `app/utils/redis_client.py`（新） | 解析 `REDIS_URL`、共享连接、失败日志 |
| `app/utils/task_store.py`（改） | 保留现有 SQLite API，供回退 |
| `app/utils/task_store_redis.py`（新） | Hash/ZSET upsert、delete、load/list、lease API |
| `app/utils/task_utils.py`（改） | 按 backend 分支；Redis 下读穿 Redis；API 签名不变 |
| `app/utils/sse_utils.py`（改） | `LocalQueueBus` / `RedisPubSubBus`；`push_to_session` / `sse_generator` 走总线 |

**SSE**

- Local：现有 `queue.Queue` 行为不变。
- Redis：`PUBLISH`；`sse_generator` `SUBSCRIBE` 后 yield 现有 SSE 帧；断开/`__close__` 退订。
- 无订阅者时 publish 正常丢弃；进度可依赖 `/status` 轮询补偿。
- 不要求跨重启恢复未消费流式事件。

## 错误处理

| 场景 | 行为 |
|------|------|
| 无 `REDIS_URL` | SQLite + 本地 SSE |
| 有 URL 但连接失败且 `REDIS_REQUIRED=0` | 日志 + 回退 SQLite |
| `REDIS_REQUIRED=1` 且连接失败 | 启动失败 |
| Redis 写任务失败 | 只打日志，不阻断导入/问答主流程（对齐现 SQLite） |
| SSE publish 失败 | 只打日志 |
| 单 worker 重启 | 其任务 lease 到期 → failed；其它 worker 任务不受影响 |

## 配置

| 变量 | 默认 | 含义 |
|------|------|------|
| `REDIS_URL` | 空 | 非空尝试启用 Redis（任务+SSE） |
| `REDIS_KEY_PREFIX` | `kb` | key 前缀 |
| `TASK_LEASE_TTL_SEC` | `30` | 租约 TTL（秒） |
| `REDIS_REQUIRED` | `0` | `1` 时连接失败则启动失败 |
| `TASK_STORE_PATH` | `data/tasks.db` | 仅 SQLite 回退 |

本机示例：`docker run -d --name kb-redis -p 6379:6379 redis:7-alpine`，`.env` 设 `REDIS_URL=redis://127.0.0.1:6379/0`。

依赖：Conda 环境安装 `redis`（redis-py）；测试可用 `fakeredis`。不引入 `pyproject.toml` / `uv`。

## 测试成功标准

1. 无 `REDIS_URL`：现有 SQLite 持久化测试仍通过。
2. fakeredis：client A 写入任务，client B 能 `list_tasks` / 读 status。
3. lease 过期后任务变为 `failed` 且带约定错误文案。
4. A `push_to_session`，B 订阅同一 session 能收到事件。
5. Redis 写失败不抛穿业务 API（只日志）。

## 文档

- `README.md`：纠正「纯内存、重启丢失」；补充 Redis 可选启动与变量。
- `docs/技术架构.md`、`docs/项目背景.md`：写明 Redis 共享 / SQLite 回退 / 租约语义。

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 每次读 Redis 增加延迟 | 任务元数据小；列表用 ZSET；不做大 value |
| Pub/Sub 无历史 | 接受；HTTP 轮询补偿进度 |
| 误开 `REDIS_REQUIRED` 导致起不来 | 默认 `0`；文档说明 |
| 与旧 SQLite 数据并存两套 | 本期不自动迁移；运维按需二选一 |
