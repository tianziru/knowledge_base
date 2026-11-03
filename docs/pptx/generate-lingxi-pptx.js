const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "灵犀智库";
pres.title = "灵犀智库 · 智能知识库架构与核心价值";
pres.subject = "RAG Knowledge Base Architecture";

// Palette: Deep Teal Knowledge (not generic purple/cream)
const C = {
  bgDark: "0B1F2A",
  bgCard: "122A36",
  bgLight: "F4F8F9",
  primary: "0E7490",
  primaryDark: "0A5568",
  accent: "14B8A6",
  accentWarm: "F59E0B",
  textDark: "0F172A",
  textMuted: "475569",
  textLight: "E2E8F0",
  white: "FFFFFF",
  line: "CBD5E1",
  danger: "E11D48",
};

const fontTitle = "Arial";
const fontBody = "Calibri";

function addFooter(slide, page, total, dark = false) {
  slide.addText("灵犀智库  ·  Knowledge Base", {
    x: 0.5,
    y: 5.25,
    w: 6,
    h: 0.25,
    fontSize: 10,
    fontFace: fontBody,
    color: dark ? "94A3B8" : "94A3B8",
    margin: 0,
  });
  slide.addText(`${page} / ${total}`, {
    x: 8.5,
    y: 5.25,
    w: 1,
    h: 0.25,
    fontSize: 10,
    fontFace: fontBody,
    color: "94A3B8",
    align: "right",
    margin: 0,
  });
}

const TOTAL = 11;

// ========== 1. Title ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625,
    fill: { color: C.bgDark },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625,
    fill: { color: C.accent },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 4.85, w: 10, h: 0.775,
    fill: { color: "081821" },
  });
  s.addText("LINGXI  ·  KNOWLEDGE BASE", {
    x: 0.7, y: 1.35, w: 8.5, h: 0.35,
    fontSize: 13, fontFace: fontTitle, color: C.accent,
    bold: true, charSpacing: 4, margin: 0,
  });
  s.addText("灵犀智库", {
    x: 0.7, y: 1.85, w: 8.5, h: 0.85,
    fontSize: 48, fontFace: fontTitle, color: C.white,
    bold: true, margin: 0,
  });
  s.addText("智能知识库架构与核心价值", {
    x: 0.7, y: 2.75, w: 8.5, h: 0.45,
    fontSize: 22, fontFace: fontBody, color: C.textLight, margin: 0,
  });
  s.addText("双流水线 RAG  ·  商品实体消歧  ·  混合检索与精排  ·  可演示可落地", {
    x: 0.7, y: 5.05, w: 8.8, h: 0.35,
    fontSize: 12, fontFace: fontBody, color: "94A3B8", margin: 0,
  });
}

// ========== 2. Agenda ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("目录", {
    x: 0.5, y: 0.28, w: 4, h: 0.4,
    fontSize: 28, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });
  const items = [
    ["01", "核心价值与问题定位"],
    ["02", "总体架构一览"],
    ["03", "导入流水线 · LangGraph"],
    ["04", "问答流水线 · 四路召回"],
    ["05", "关键技术栈与组件"],
    ["06", "差异化能力拆解"],
    ["07", "演示路径与落地价值"],
    ["08", "总结与展望"],
  ];
  items.forEach((it, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i % 4;
    const x = 0.5 + col * 4.7;
    const y = 1.25 + row * 0.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 4.4, h: 0.72,
      fill: { color: C.white },
      rectRadius: 0.08,
      shadow: { type: "outer", color: "0B1F2A", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
    });
    s.addText(it[0], {
      x: x + 0.2, y: y + 0.18, w: 0.7, h: 0.4,
      fontSize: 18, fontFace: fontTitle, color: C.primary, bold: true, margin: 0,
    });
    s.addText(it[1], {
      x: x + 1.0, y: y + 0.2, w: 3.2, h: 0.35,
      fontSize: 15, fontFace: fontBody, color: C.textDark, margin: 0,
    });
  });
  addFooter(s, 2, TOTAL);
}

// ========== 3. Core Value ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("核心价值：不止于「能搜到」，而是「答得对」", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 22, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  const cards = [
    { t: "业务闭环", d: "导入时识别商品实体，问答时先确认再检索，避免串型号、答非所问。" },
    { t: "工业检索栈", d: "稠密+稀疏混合向量 → RRF 多路融合 → Cross-Encoder 精排，召回质量可控。" },
    { t: "可编排可观测", d: "LangGraph 双流水线，节点进度可视化；导入后台与问答前台可独立演示。" },
    { t: "多源互补", d: "向量库 / 知识图谱 / HyDE / 联网 MCP 并行，覆盖私有知识与公开信息。" },
  ];
  cards.forEach((c, i) => {
    const x = 0.4 + (i % 2) * 4.7;
    const y = 1.2 + Math.floor(i / 2) * 1.85;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: 4.4, h: 1.65,
      fill: { color: C.white },
      rectRadius: 0.1,
      shadow: { type: "outer", color: "0B1F2A", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.12, h: 1.65, fill: { color: i % 2 === 0 ? C.accent : C.primary },
    });
    s.addText(c.t, {
      x: x + 0.35, y: y + 0.25, w: 3.8, h: 0.35,
      fontSize: 18, fontFace: fontTitle, color: C.textDark, bold: true, margin: 0,
    });
    s.addText(c.d, {
      x: x + 0.35, y: y + 0.7, w: 3.8, h: 0.75,
      fontSize: 13, fontFace: fontBody, color: C.textMuted, margin: 0,
    });
  });
  addFooter(s, 3, TOTAL);
}

// ========== 4. Architecture ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("总体架构：导入与问答双流水线", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 24, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  // Left: Import
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.35, y: 1.15, w: 4.5, h: 3.85,
    fill: { color: C.white }, rectRadius: 0.1,
    shadow: { type: "outer", color: "0B1F2A", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.35, y: 1.15, w: 4.5, h: 0.55, fill: { color: C.primary },
  });
  s.addText("导入服务  :8000", {
    x: 0.55, y: 1.25, w: 4, h: 0.35,
    fontSize: 16, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });
  s.addText([
    { text: "PDF / MD / Office 上传", options: { breakLine: true } },
    { text: "MinerU 解析 → Markdown", options: { breakLine: true } },
    { text: "图片处理 · MinIO", options: { breakLine: true } },
    { text: "文档切分", options: { breakLine: true } },
    { text: "LLM 商品名识别", options: { breakLine: true } },
    { text: "BGE-M3 混合向量", options: { breakLine: true } },
    { text: "Milvus 入库", options: { breakLine: false } },
  ], {
    x: 0.65, y: 1.9, w: 3.9, h: 2.8,
    fontSize: 14, fontFace: fontBody, color: C.textDark,
    paraSpacing: 8, bullet: false, margin: 0,
  });

  // Right: Query
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.15, y: 1.15, w: 4.5, h: 3.85,
    fill: { color: C.white }, rectRadius: 0.1,
    shadow: { type: "outer", color: "0B1F2A", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.15, y: 1.15, w: 4.5, h: 0.55, fill: { color: C.accent },
  });
  s.addText("问答服务  :8001", {
    x: 5.35, y: 1.25, w: 4, h: 0.35,
    fontSize: 16, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });
  s.addText([
    { text: "商品意图确认 / 反问", options: { breakLine: true } },
    { text: "向量检索 + HyDE", options: { breakLine: true } },
    { text: "知识图谱 Neo4j", options: { breakLine: true } },
    { text: "联网搜索 MCP", options: { breakLine: true } },
    { text: "RRF 多路融合", options: { breakLine: true } },
    { text: "BGE Reranker 精排", options: { breakLine: true } },
    { text: "LLM 生成 + SSE 流式", options: { breakLine: false } },
  ], {
    x: 5.45, y: 1.9, w: 3.9, h: 2.8,
    fontSize: 14, fontFace: fontBody, color: C.textDark,
    paraSpacing: 8, margin: 0,
  });
  addFooter(s, 4, TOTAL);
}

// ========== 5. Import Pipeline ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("导入流水线：从文件到可检索资产", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 24, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  const steps = [
    { n: "1", t: "入口分流", d: "PDF / MD / Office" },
    { n: "2", t: "解析成 MD", d: "MinerU / 转换" },
    { n: "3", t: "图片处理", d: "路径修复·存储" },
    { n: "4", t: "文档切分", d: "检索粒度" },
    { n: "5", t: "商品识别", d: "LLM 实体" },
    { n: "6", t: "向量化", d: "BGE-M3" },
    { n: "7", t: "入库", d: "Milvus" },
  ];
  steps.forEach((st, i) => {
    const x = 0.28 + i * 1.38;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.35, w: 1.28, h: 2.4,
      fill: { color: C.white }, rectRadius: 0.08,
      shadow: { type: "outer", color: "0B1F2A", blur: 6, offset: 1, angle: 135, opacity: 0.1 },
    });
    s.addShape(pres.shapes.OVAL, {
      x: x + 0.34, y: 1.55, w: 0.55, h: 0.55,
      fill: { color: i === 4 ? C.accentWarm : C.primary },
    });
    s.addText(st.n, {
      x: x + 0.34, y: 1.62, w: 0.55, h: 0.4,
      fontSize: 16, fontFace: fontTitle, color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addText(st.t, {
      x: x + 0.08, y: 2.3, w: 1.12, h: 0.7,
      fontSize: 13, fontFace: fontTitle, color: C.textDark, bold: true, align: "center", margin: 0,
    });
    s.addText(st.d, {
      x: x + 0.08, y: 3.1, w: 1.12, h: 0.45,
      fontSize: 11, fontFace: fontBody, color: C.textMuted, align: "center", margin: 0,
    });
    if (i < steps.length - 1) {
      s.addShape(pres.shapes.RIGHT_ARROW, {
        x: x + 1.18, y: 2.35, w: 0.22, h: 0.2,
        fill: { color: C.accent },
      });
    }
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.35, y: 4.0, w: 9.3, h: 0.95,
    fill: { color: C.bgDark }, rectRadius: 0.08,
  });
  s.addText("技术要点：条件边分流（PDF ↔ MD）→ 统一后续节点；商品名写入独立集合，与切片集合解耦，支撑问答侧消歧。", {
    x: 0.55, y: 4.2, w: 8.9, h: 0.55,
    fontSize: 13, fontFace: fontBody, color: C.textLight, margin: 0,
  });
  addFooter(s, 5, TOTAL);
}

// ========== 6. Query Pipeline ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("问答流水线：确认 → 并行召回 → 融合精排 → 生成", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 22, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  // Top confirm
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 2.5, y: 1.15, w: 5, h: 0.55,
    fill: { color: C.primary }, rectRadius: 0.08,
  });
  s.addText("商品确认  ·  唯一命中继续 / 模糊则反问直出", {
    x: 2.5, y: 1.25, w: 5, h: 0.35,
    fontSize: 13, fontFace: fontBody, color: C.white, align: "center", bold: true, margin: 0,
  });

  // Four parallel
  const lanes = [
    { t: "向量检索", s: "Query → Milvus" },
    { t: "HyDE", s: "假想文档检索" },
    { t: "知识图谱", s: "Neo4j 关系" },
    { t: "联网 MCP", s: "WebSearch" },
  ];
  lanes.forEach((l, i) => {
    const x = 0.4 + i * 2.4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 2.0, w: 2.2, h: 1.15,
      fill: { color: C.white }, rectRadius: 0.08,
      shadow: { type: "outer", color: "0B1F2A", blur: 6, offset: 1, angle: 135, opacity: 0.1 },
    });
    s.addText(l.t, {
      x, y: 2.2, w: 2.2, h: 0.35,
      fontSize: 14, fontFace: fontTitle, color: C.textDark, bold: true, align: "center", margin: 0,
    });
    s.addText(l.s, {
      x, y: 2.6, w: 2.2, h: 0.35,
      fontSize: 12, fontFace: fontBody, color: C.textMuted, align: "center", margin: 0,
    });
  });

  // Bottom funnel
  const funnel = [
    { t: "RRF 融合", c: C.primary },
    { t: "Rerank 精排", c: C.accent },
    { t: "LLM 生成", c: C.primaryDark },
  ];
  funnel.forEach((f, i) => {
    const x = 1.2 + i * 2.7;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 3.5, w: 2.4, h: 0.7,
      fill: { color: f.c }, rectRadius: 0.08,
    });
    s.addText(f.t, {
      x, y: 3.65, w: 2.4, h: 0.4,
      fontSize: 15, fontFace: fontTitle, color: C.white, bold: true, align: "center", margin: 0,
    });
  });

  s.addText("并行召回扩大覆盖面，RRF 稳住多源排序，Reranker 把「最相关」推到生成上下文前排。", {
    x: 0.5, y: 4.5, w: 9, h: 0.4,
    fontSize: 13, fontFace: fontBody, color: C.textMuted, margin: 0,
  });
  addFooter(s, 6, TOTAL);
}

// ========== 7. Tech Stack ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("关键技术栈与组件", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 24, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  const rows = [
    ["编排", "LangGraph + FastAPI", "有状态图、条件边、并行节点；导入/问答双服务"],
    ["解析", "MinerU + python-docx/pptx", "PDF/Office → 统一 Markdown 中间态"],
    ["向量", "BGE-M3 + BGE-Reranker", "稠密+稀疏混合嵌入；交叉编码精排"],
    ["存储", "Milvus · Neo4j · Mongo · MinIO", "切片/实体 · 图谱 · 会话 · 对象"],
    ["智能", "Qwen (DashScope) + MCP", "识别/HyDE/生成；联网搜索补全"],
  ];
  rows.forEach((r, i) => {
    const y = 1.15 + i * 0.72;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.4, y, w: 9.2, h: 0.62,
      fill: { color: C.white }, rectRadius: 0.06,
    });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y: y + 0.12, w: 1.1, h: 0.38,
      fill: { color: i % 2 === 0 ? C.primary : C.accent }, rectRadius: 0.06,
    });
    s.addText(r[0], {
      x: 0.5, y: y + 0.16, w: 1.1, h: 0.3,
      fontSize: 12, fontFace: fontTitle, color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addText(r[1], {
      x: 1.8, y: y + 0.16, w: 3.3, h: 0.3,
      fontSize: 13, fontFace: fontBody, color: C.textDark, bold: true, margin: 0,
    });
    s.addText(r[2], {
      x: 5.2, y: y + 0.16, w: 4.2, h: 0.3,
      fontSize: 12, fontFace: fontBody, color: C.textMuted, margin: 0,
    });
  });
  addFooter(s, 7, TOTAL);
}

// ========== 8. Differentiators ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("差异化能力：相对通用 RAG 多走的三步", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 22, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  const diffs = [
    {
      n: "01",
      t: "商品实体层",
      d: "导入识别 item_name，问答先确认。模糊时反问，不硬答，从源头降低幻觉与串货风险。",
    },
    {
      n: "02",
      t: "混合检索 + 精排",
      d: "BGE-M3 语义与关键词兼顾；RRF 融合多路结果；Reranker 做最后一道相关性闸门。",
    },
    {
      n: "03",
      t: "HyDE + 图谱 + 联网",
      d: "短查询用假想文档拉近语义空间；图谱补结构；MCP 补库外事实，形成私有+公开组合拳。",
    },
  ];
  diffs.forEach((d, i) => {
    const y = 1.2 + i * 1.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.4, y, w: 9.2, h: 1.05,
      fill: { color: C.white }, rectRadius: 0.08,
      shadow: { type: "outer", color: "0B1F2A", blur: 6, offset: 1, angle: 135, opacity: 0.08 },
    });
    s.addText(d.n, {
      x: 0.6, y: y + 0.28, w: 0.9, h: 0.5,
      fontSize: 22, fontFace: fontTitle, color: C.accent, bold: true, margin: 0,
    });
    s.addText(d.t, {
      x: 1.6, y: y + 0.18, w: 7.7, h: 0.35,
      fontSize: 16, fontFace: fontTitle, color: C.textDark, bold: true, margin: 0,
    });
    s.addText(d.d, {
      x: 1.6, y: y + 0.55, w: 7.7, h: 0.4,
      fontSize: 13, fontFace: fontBody, color: C.textMuted, margin: 0,
    });
  });
  addFooter(s, 8, TOTAL);
}

// ========== 9. Demo Path ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("推荐演示路径（15 分钟）", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 24, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  const demos = [
    { t: "上传 PDF", d: "跟节点进度：解析→切分→识别→入库", m: "3′" },
    { t: "查 Milvus", d: "展示切片与商品实体集合", m: "2′" },
    { t: "精准问答", d: "四路召回 + RRF + Rerank + 生成", m: "4′" },
    { t: "模糊反问", d: "商品确认节点直接输出选项", m: "3′" },
    { t: "收束价值", d: "对照「通用 RAG」差异点复盘", m: "3′" },
  ];
  demos.forEach((d, i) => {
    const x = 0.3 + i * 1.92;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.3, w: 1.8, h: 3.2,
      fill: { color: C.white }, rectRadius: 0.1,
      shadow: { type: "outer", color: "0B1F2A", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.3, w: 1.8, h: 0.7, fill: { color: C.bgDark },
    });
    s.addText(d.m, {
      x, y: 1.45, w: 1.8, h: 0.4,
      fontSize: 20, fontFace: fontTitle, color: C.accent, bold: true, align: "center", margin: 0,
    });
    s.addText(d.t, {
      x: x + 0.1, y: 2.25, w: 1.6, h: 0.7,
      fontSize: 15, fontFace: fontTitle, color: C.textDark, bold: true, align: "center", margin: 0,
    });
    s.addText(d.d, {
      x: x + 0.12, y: 3.1, w: 1.56, h: 1.1,
      fontSize: 12, fontFace: fontBody, color: C.textMuted, align: "center", margin: 0,
    });
  });
  addFooter(s, 9, TOTAL);
}

// ========== 10. Summary ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgLight },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.bgDark },
  });
  s.addText("一句话总结", {
    x: 0.5, y: 0.28, w: 9, h: 0.4,
    fontSize: 24, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.3, w: 9, h: 1.4,
    fill: { color: C.bgDark }, rectRadius: 0.1,
  });
  s.addText("灵犀智库 = 可编排的双流水线 RAG + 商品实体消歧 + 工业级检索精排，\n让私有知识「进得去、找得准、答得稳」。", {
    x: 0.8, y: 1.55, w: 8.4, h: 1.0,
    fontSize: 18, fontFace: fontBody, color: C.white, align: "center", margin: 0,
  });

  const takeaways = [
    { t: "架构清晰", d: "导入 / 问答解耦，端口与职责分明" },
    { t: "价值可证", d: "演示路径与节点进度一一对应" },
    { t: "技术扎实", d: "混合向量、RRF、Rerank、HyDE、MCP" },
  ];
  takeaways.forEach((t, i) => {
    const x = 0.5 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 3.1, w: 2.9, h: 1.5,
      fill: { color: C.white }, rectRadius: 0.1,
      shadow: { type: "outer", color: "0B1F2A", blur: 8, offset: 2, angle: 135, opacity: 0.08 },
    });
    s.addText(t.t, {
      x, y: 3.35, w: 2.9, h: 0.4,
      fontSize: 16, fontFace: fontTitle, color: C.primary, bold: true, align: "center", margin: 0,
    });
    s.addText(t.d, {
      x: x + 0.15, y: 3.85, w: 2.6, h: 0.55,
      fontSize: 13, fontFace: fontBody, color: C.textMuted, align: "center", margin: 0,
    });
  });
  addFooter(s, 10, TOTAL);
}

// ========== 11. Closing ==========
{
  const s = pres.addSlide();
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.bgDark },
  });
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: C.accent },
  });
  s.addText("谢谢", {
    x: 0.7, y: 1.8, w: 8.5, h: 0.8,
    fontSize: 48, fontFace: fontTitle, color: C.white, bold: true, margin: 0,
  });
  s.addText("灵犀智库  ·  智能知识库", {
    x: 0.7, y: 2.7, w: 8.5, h: 0.4,
    fontSize: 20, fontFace: fontBody, color: C.accent, margin: 0,
  });
  s.addText("导入  :8000    问答  :8001", {
    x: 0.7, y: 3.4, w: 8.5, h: 0.35,
    fontSize: 14, fontFace: fontBody, color: "94A3B8", margin: 0,
  });
  s.addText("欢迎交流架构、演示与落地路径", {
    x: 0.7, y: 4.6, w: 8.5, h: 0.35,
    fontSize: 14, fontFace: fontBody, color: "64748B", margin: 0,
  });
}

const out = path.join(__dirname, "灵犀智库-架构与核心价值.pptx");
pres.writeFile({ fileName: out }).then(() => {
  console.log("Wrote", out);
});
