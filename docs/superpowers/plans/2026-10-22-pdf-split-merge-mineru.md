# PDF 超页自动拆分再合并（MinerU）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当 PDF 超过可配置页数阈值时，在 `node_pdf_to_md` 内自动拆分、有限并行调用 MinerU、合并为单一 MD，下游节点无感。

**Architecture:** 纯函数拆分/合并抽到 `pdf_split.py`；`node_pdf_to_md` 编排页数判定、ThreadPool 有限并行、段级重试；配置进 `MineruConfig`。

**Tech Stack:** PyMuPDF (`fitz`)、`concurrent.futures`、现有 MinerU HTTP 流程、FastAPI 导入图。

## Global Constraints

- 默认 `MINERU_MAX_PAGES=180`，实现时若配置 >200 则 clamp 到 200 并 warning
- 默认并发 `MINERU_SPLIT_CONCURRENCY=2`；段失败重试 `MINERU_PART_RETRIES=2`，耗尽后整单失败
- 合并后 MD/图片布局与现网一致：`{local_dir}/{stem}/{stem}.md` + 同级 `images/`
- 不新增 LangGraph 节点；不擅自 git commit（除非用户要求）

---

### Task 1: 配置扩展

**Files:**
- Modify: `app/conf/mineru_config.py`
- Modify: `.env`（追加注释项）

- [x] **Step 1:** 扩展 `MineruConfig` 字段并在构造时读取/解析/clamp

```python
@dataclass
class MineruConfig:
    base_url: str
    api_key: str
    max_pages: int = 180
    split_concurrency: int = 2
    part_retries: int = 2
```

解析逻辑：`int(os.getenv(...))`，非法则用默认；`max_pages = min(max(1, max_pages), 200)`。

- [x] **Step 2:** `.env` 增加三行配置注释默认值

---

### Task 2: 拆分与合并纯函数 + 单测

**Files:**
- Create: `app/import_process/utils/pdf_split.py`
- Create: `test/06-test_pdf_split_merge.py`

**Produces:**
- `compute_page_ranges(total_pages: int, max_pages: int) -> list[tuple[int, int]]`  # 1-based inclusive
- `split_pdf_by_pages(pdf_path: Path, out_dir: Path, max_pages: int) -> list[tuple[Path, int, int]]`
- `rewrite_image_refs(md: str, rename_map: dict[str, str]) -> str`
- `merge_part_markdowns(part_md_dirs: list[Path], final_dir: Path, stem: str) -> Path`
  - `part_md_dirs` 已按页序排好；每目录内含 md + 可选 `images/`
  - 返回最终 md Path

- [x] **Step 1:** 写失败单测（ranges / rename / merge 顺序）
- [x] **Step 2:** 实现纯函数使测试通过

---

### Task 3: 接入 `node_pdf_to_md`

**Files:**
- Modify: `app/import_process/agent/nodes/node_pdf_to_md.py`

- [x] **Step 1:** 页数 ≤ `max_pages` 保持原 `step_2`/`step_3` 路径
- [x] **Step 2:** 超出则 `split_pdf_by_pages` → `ThreadPoolExecutor` 调现有 upload/poll/extract（每段独立 out 目录）
- [x] **Step 3:** 段失败重试；全部成功后 `merge_part_markdowns`，写 `state["md_path"]`/`md_content`
- [x] **Step 4:** 按段数放大节点侧日志说明；单段 poll 超时保持 600s

---

### Task 4: 文档

**Files:**
- Modify: `README.md`
- Modify: `docs/技术架构.md`
- Modify: design spec 状态为已批准待落地/已实现

- [x] **Step 1:** README 增加超长 PDF 自动拆分说明与三个环境变量
- [x] **Step 2:** 技术架构导入管线补一句

---

## Spec coverage

| Spec 项 | Task |
|---------|------|
| 可配置 max_pages / concurrency / retries | 1 |
| fitz 拆分、合并、图片冲突 | 2 |
| 有限并行 + 重试 + 整单失败 | 3 |
| 下游透明 | 3 |
| README / 架构文档 | 4 |
