# 导入任务状态 SQLite 持久化设计

**日期：** 2026-10-28  
**状态：** 已批准（用户确认方案 1 + SQLite + 完整字段）

## 背景与问题

导入后台「文档导入」列表显示本地 `localStorage` 中的已完成任务，概览「已完成」来自 `GET /stats`，而 `/stats` 只统计进程内存 `_tasks_status`。服务重启后内存清空，概览归零，列表仍显示已完成，两边不一致。架构文档已将「任务状态非持久化」列为已知债务。

## 目标

后端用 SQLite 持久化任务状态与节点进度，使服务重启后 `/stats`、`/tasks`、`/status` 与概览「已完成」仍正确；调用方 API 尽量不变。

## 方案

**方案 1：`task_utils` 写穿到 SQLite（已选）**

- 内存字典仍作热缓存。
- 写操作改内存后立即 upsert/delete 到 `data/tasks.db`。
- 进程启动时从 DB 加载；将仍为 `pending`/`processing` 的任务标为 `failed`（不做自动续跑）。

未选：独立 TaskStore 显式改造所有调用点；纯 JSON 整表读写。

## 范围

### 做

1. 新增 `app/utils/task_store.py`：SQLite 建表、读写、线程安全连接。
2. 改造 `app/utils/task_utils.py`：写穿 + 启动加载 + 中断任务标记 failed。
3. 持久化字段：`task_id`、`status`、`file_name`、`file_size`、`created_at`、`updated_at`、`done_list`、`running_list`、`error`。
4. 默认库路径 `data/tasks.db`；`data/` 不存在则创建；可选环境变量覆盖路径。
5. 更新架构文档中「任务状态非持久化」相关表述。

### 不做

- 多 worker / Redis / 分布式锁
- 从浏览器 localStorage 回填历史任务
- 运行中任务自动续跑
- 前端 localStorage 合并逻辑改造
- 查询侧 result（如 answer）全量持久化（仅持久 `error`）

## 架构

```
节点 / file_import_service
        │
        ▼
   task_utils API（不变）
        │
        ├─► 内存字典（热缓存）
        └─► task_store（SQLite 写穿）

启动：task_store.load_all() → 填充内存
      → pending/processing → failed + 清空 running_list → 写回 DB

GET /stats|/tasks|/status → 仍只读 task_utils 内存（已含持久化数据）
```

## 数据模型

表名：`tasks`（一行一任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | TEXT PK | |
| `status` | TEXT | pending / processing / completed / failed |
| `file_name` | TEXT | |
| `file_size` | INTEGER | |
| `created_at` | TEXT | ISO |
| `updated_at` | TEXT | ISO，每次写穿更新 |
| `done_list` | TEXT | JSON 数组，存原始节点 ID |
| `running_list` | TEXT | JSON 数组，存原始节点 ID |
| `error` | TEXT | 来自 `set_task_result(..., "error")` |

## 写入时机

| 触发 API | 行为 |
|----------|------|
| `register_task_meta` | upsert meta 字段 |
| `update_task_status` | upsert status |
| `add_running_task` / `add_done_task` | upsert 对应 list（done 时同步 running） |
| `set_task_result`（key=`error`） | upsert error |
| `clear_task` | DELETE 行 |

并发：单连接 + 线程锁。写库失败只打日志，不阻断导入主流程。

## 启动与中断策略

1. `CREATE TABLE IF NOT EXISTS`
2. 全量加载到内存
3. 对 `status in (pending, processing)`：设为 `failed`，`error` 设为「服务重启，任务中断」，`running_list` 清空，写回 DB

## 调用方影响

- `file_import_service`、导入/查询各节点：**无需改业务逻辑**
- 导入与查询共用 `task_utils`，查询 session 也会进库（可接受）
- 前端可不改；新任务起概览与列表应对齐服务端

## 错误处理

- 写失败：日志告警，内存仍更新；后续成功写入可覆盖
- DB 缺失：建新库；损坏无法读时告警并以空状态启动
- `data/` 缺失：启动时创建

## 成功标准

1. 完成 2 个导入任务后，概览「已完成」= 2，与任务列表一致。
2. 重启导入服务后不重新导入：概览「已完成」仍为 2；`/tasks` 仍有这两条。
3. 重启时若有进行中任务：变为 failed，error 含重启说明，running 为空。
4. 删除任务后 DB 与 `/stats` 同步减少。
5. 现有导入/查询 API 与前端无需强制改动即可工作。

## 测试要点

- 单元：task_store upsert/load/delete；task_utils 写穿后重启模拟（新进程或 reload）仍可读
- 手工：导入完成 → 看概览 → 重启服务 → 再看概览与 `/stats`
