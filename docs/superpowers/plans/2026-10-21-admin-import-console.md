# Admin Import Console Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** 灵犀智库导入页升级为后台壳子，并支持 txt/docx/pptx 等格式真入库。

**Architecture:** 单页 `import.html` SPA；`office_to_md` 工具在 `node_entry` 将办公文档转为 MD 后走现有 MD 分支；新增 `/stats`；上传扩展名校验。

**Tech Stack:** FastAPI, LangGraph, python-docx, python-pptx, vanilla HTML/CSS/JS

## Global Constraints

- 品牌文案：灵犀智库
- 不做登录/权限
- `.doc`/`.ppt` 不引入 LibreOffice，失败即明确报错
- 不另起前端框架

---

### Task 1: office_to_md 工具 + 依赖

**Files:**
- Create: `app/import_process/utils/__init__.py`
- Create: `app/import_process/utils/office_to_md.py`
- 依赖：在 Conda 环境 `knowledge_base` 中安装 `python-docx`、`python-pptx`

- [ ] 实现 `SUPPORTED_OFFICE_EXTS`、`convert_to_md(src_path, dest_dir) -> str`
- [ ] txt/docx/pptx 分别实现；doc/ppt raise ValueError 明确信息
- [ ] `uv add` / pip 安装依赖

### Task 2: node_entry 接入

**Files:**
- Modify: `app/import_process/agent/nodes/node_entry.py`
- Modify: `app/utils/task_utils.py`（可选：转换步骤中文名）

- [ ] 后缀分支：pdf / md / office → convert → md_path + is_md_read_enabled
- [ ] 不支持格式：记录错误，不置开关（路由 END）；或 raise 让 run_graph_task 标 failed

### Task 3: API 校验与 stats

**Files:**
- Modify: `app/import_process/api/file_import_service.py`

- [ ] 上传白名单扩展名
- [ ] `GET /stats`：total/by_status/today
- [ ] 更新 FastAPI description

### Task 4: import.html 后台壳子

**Files:**
- Modify: `app/import_process/page/import.html`

- [ ] 侧栏 + 四面板
- [ ] 概览拉 `/stats` + `/tasks`
- [ ] 导入区多格式 accept
- [ ] 任务中心筛选/搜索
- [ ] STORAGE_KEY v4

### Task 5: 冒烟验证

- [x] 用小 txt 测 convert + entry 逻辑（可本地单元调用）
- [x] 确认页面静态资源可打开
- [x] `/stats` 与 txt 上传已在 8000 服务验证（转换节点出现在 done_list）
