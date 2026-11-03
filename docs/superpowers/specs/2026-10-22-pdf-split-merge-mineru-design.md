# PDF 超页自动拆分再合并（MinerU）· 设计说明

日期：2026-10-22  
状态：已实现（2026-10-22）

## 1. 背景与问题

导入链路中 `node_pdf_to_md` 将整本 PDF 上传到 MinerU 云端解析。MinerU 对单文件有 **200 页** 上限；超过时轮询返回：

`number of pages exceeds limit (200 pages), please split the file and try again`

当前节点无拆分逻辑，长手册导入直接失败。下游切分 / `item_name` 识别 / 向量入库期望的是 **一份完整 MD**，不宜把一本手册拆成多个导入任务。

## 2. 目标

- 页数超过可配置阈值时，**自动按页拆分 → 有限并行调用 MinerU → 合并为单一 MD**（含图片路径整理）。
- 对 LangGraph 其余节点与导入 API **透明**：仍产出单个 `md_path` / `md_content`。
- 任一段在重试耗尽后仍失败 → **整单失败**（不产出残缺手册）。

非目标：

- 不新增独立 LangGraph 节点。
- 不在前端拆成多个上传任务。
- 不改变 `item_name` 幂等与 Milvus 写入语义。
- 不做目录感知拆分（按固定页窗即可）。

## 3. 已确认决策

| 项 | 选择 |
|----|------|
| 架构 | 在 `node_pdf_to_md` 内透明增强（方案 1） |
| 并发 | 有限并行，默认并发度 **2**（可配置） |
| 失败 | 单段失败自动重试，耗尽后 **整单失败** |
| 页窗 | 可配置，默认 **180**（低于硬上限 200，留余量） |
| 拆分库 | 使用环境已有 **PyMuPDF (`fitz`)** |

## 4. 架构与数据流

```
node_pdf_to_md
  ├─ 读页数 (fitz)
  ├─ pages ≤ max_pages ──► 现有：upload → poll → download/extract → md
  └─ pages > max_pages
        ├─ 拆分为 part PDFs（local_dir/pdf_parts/）
        ├─ ThreadPoolExecutor(max_workers=concurrency)
        │     每段：upload → poll → download/extract（失败则重试）
        ├─ 按页序合并 MD + 归一化 images/
        └─ 写出与现网一致的 {stem}.md，写入 state
```

下游不变：`node_md_img` → `node_document_split` → …

## 5. 组件职责

### 5.1 配置（`app/conf/mineru_config.py` + `.env`）

在现有 `MineruConfig` 上扩展：

| 环境变量 | 默认 | 含义 |
|----------|------|------|
| `MINERU_MAX_PAGES` | `180` | 单段最大页数；≤ 此值不拆分 |
| `MINERU_SPLIT_CONCURRENCY` | `2` | 同时处理的段数上限 |
| `MINERU_PART_RETRIES` | `2` | 单段失败后的额外重试次数（共 1+retries 次尝试） |

保留现有 `MINERU_BASE_URL` / `MINERU_API_TOKEN`。硬上限 200 仅作文档说明，代码以 `MINERU_MAX_PAGES` 为准；若配置值 > 200，实现时应 **clamp 到 200** 并打 warning，避免再次触发云端拒收。

### 5.2 拆分（新建小工具或同文件私有函数）

- 输入：原 PDF `Path`、输出目录、`max_pages`。
- 输出：有序列表 `[(part_pdf_path, page_start, page_end), ...]`（页码 1-based，便于日志）。
- 命名：`{stem}_p{start}-{end}.pdf`，目录：`{local_dir}/pdf_parts/`。
- 使用 `fitz` 按页拷贝写入；不改原 PDF。

### 5.3 单段解析

复用现有 `step_2_upload_and_poll` / `step_3_download_and_extract`（可小幅参数化超时）。每段输出目录建议：

`{local_dir}/pdf_parts_out/{stem}_p{start}-{end}/`

避免多段解压互相覆盖。

单段包装逻辑：

1. 调用 upload/poll/extract。
2. 失败则最多再试 `MINERU_PART_RETRIES` 次（指数或固定间隔均可，建议固定 5s）。
3. 仍失败：抛出，携带段标识与最后错误信息；上层取消未完成任务并失败整单。

### 5.4 有限并行

- `concurrent.futures.ThreadPoolExecutor(max_workers=MINERU_SPLIT_CONCURRENCY)`。
- 提交全部段任务；`as_completed` 收集结果。
- 任一 future 最终失败：记录错误，尽量 `cancel` 未开始的，已在飞的等其结束或自然失败，然后 `raise`。
- 成功结果按 **page_start** 排序后再合并（不以完成时间为序）。

### 5.5 合并 MD 与图片

MinerU 各段常见结构：`full.md` 或同名 md + `images/`。合并规则：

1. 创建最终目录：`{local_dir}/{stem}/`（与现网单文件解压目标一致）。
2. 统一 `images/`：拷贝各段图片；若文件名冲突，重命名为 `p{part_index}_{original}`，并改写该段 MD 内对应引用。
3. 按段序拼接 MD 正文；段间插入空行；可选一行 HTML 注释标记页范围（便于排障，不影响切分语义）。
4. 写出 `{local_dir}/{stem}/{stem}.md`，`state["md_path"]` / `state["md_content"]` 与现逻辑一致。

`node_md_img` 仍从 MD 同级 `images/` 取图，故合并后必须保证该约定成立。

### 5.6 超时

当前单次 poll 上限约 600s。拆分路径下：

- 单段仍用原 poll 超时；或  
- 节点级总超时 ≈ `ceil(num_parts / concurrency) * per_part_timeout`（实现时取合理上界并打日志）。

至少保证：多段场景不会在第一段还在跑时就因「整节点假超时」误杀（若保留单一 while 超时，需按段数放大）。

### 5.7 任务进度与日志

- 继续使用现有 `add_running_task` / `add_done_task`（节点级一次）。
- 日志需包含：总页数、是否拆分、段数、每段起止页、batch_id、重试次数、合并后 MD 路径。
- 不要求把每段进度拆成多个 UI 任务（YAGNI）；导入页仍显示 `node_pdf_to_md` 进行中即可。

## 6. 错误处理

| 场景 | 行为 |
|------|------|
| 页数 ≤ max_pages | 走原单文件路径 |
| 拆分后某段上传/轮询/下载失败 | 重试至上限后整单失败，错误信息带段名与 `err_msg` |
| 某段 done 但无 MD | 视为该段失败，进入重试/整单失败 |
| 配置 max_pages > 200 | clamp 到 200 + warning |
| fitz 无法打开 PDF | 立即失败，明确日志 |

## 7. 测试要点

- 单元：页数计算；按 180 页拆分边界（180→1 段不拆；181→2 段；360→2 段；361→3 段）。
- 单元：图片重名冲突时重命名与 MD 链接改写。
- 单元：合并顺序严格按 page_start。
- 集成（可选/手动）：小 PDF 不拆分路径回归；长 PDF（或人为把 max_pages 设为 2）走拆分合并路径。
- 失败：mock 某段始终失败，断言整单 raise 且重试次数符合配置。

## 8. 文档与配置落地

- `.env` 增加上述三个变量（附注释）。
- `README.md` 简短说明：超长 PDF 会自动拆分再合并；可调 `MINERU_MAX_PAGES` 等。
- `docs/技术架构.md` 导入管线处补一句「PDF>阈值时节点内拆分并行 MinerU 再合并」。

## 9. 实现范围（文件）

| 文件 | 变更 |
|------|------|
| `app/conf/mineru_config.py` | 扩展字段与默认值 |
| `app/import_process/agent/nodes/node_pdf_to_md.py` | 拆分/并行/合并编排；≤阈值走原路径 |
| 可选 `app/import_process/utils/pdf_split.py` | 若节点文件过长则抽出拆分与合并纯函数 |
| `.env` / `README.md` / `docs/技术架构.md` | 配置与说明 |

不改：查询侧、其它导入节点、前端 HTML（除非后续要展示段进度）。
