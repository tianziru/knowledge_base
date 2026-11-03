/**
 * 灵犀智库 · 高端 AI 风格答辩/汇报 PPT
 * 视觉：深空底 + 青霓虹强调 + 几何网格点阵（非通用紫白）
 */
const pptxgen = require("pptxgenjs");
const path = require("path");

const pres = new pptxgen();
pres.defineLayout({ name: "WIDE_AI", width: 13.333, height: 7.5 });
pres.layout = "WIDE_AI";
pres.author = "灵犀智库";
pres.title = "面向设备手册的多模态多路融合检索智能问答系统";
pres.subject = "Dual LangGraph · Hybrid Retrieval · Multimodal RAG";

const C = {
  void: "050816",
  deep: "0A1024",
  panel: "111827",
  panel2: "0F172A",
  line: "1E293B",
  cyan: "22D3EE",
  cyanDim: "0891B2",
  mint: "2DD4BF",
  ice: "E0F2FE",
  muted: "94A3B8",
  soft: "CBD5E1",
  white: "FFFFFF",
  warn: "FBBF24",
  rose: "FB7185",
};

const FT = "Arial";
const FB = "Calibri";
const TOTAL = 22;

function mesh(slide) {
  // subtle geometric dots / lines for AI atmosphere
  const dots = [
    [0.4, 0.5], [1.2, 1.8], [2.5, 0.9], [11.8, 1.2], [12.6, 2.4],
    [12.2, 5.8], [0.8, 6.2], [3.2, 6.8], [10.5, 0.4], [6.5, 0.35],
  ];
  for (const [x, y] of dots) {
    slide.addShape(pres.shapes.OVAL, {
      x, y, w: 0.06, h: 0.06,
      fill: { color: C.cyan, transparency: 55 },
      line: { color: C.cyan, transparency: 100 },
    });
  }
  slide.addShape(pres.shapes.LINE, {
    x: 0.5, y: 0.55, w: 2.0, h: 1.2,
    line: { color: C.cyan, width: 0.75, transparency: 80 },
  });
  slide.addShape(pres.shapes.LINE, {
    x: 11.5, y: 1.3, w: 1.2, h: 1.0,
    line: { color: C.mint, width: 0.75, transparency: 80 },
  });
}

function darkBg(slide) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.333, h: 7.5,
    fill: { color: C.void },
  });
  // left neon rail
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 7.5,
    fill: { color: C.cyan },
  });
  // top glow bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.12, y: 0, w: 13.213, h: 0.06,
    fill: { color: C.cyanDim },
  });
  mesh(slide);
}

function footer(slide, n) {
  slide.addText("LINGXI  ·  MULTIMODAL RAG  ·  DUAL LANGGRAPH", {
    x: 0.45, y: 7.12, w: 9, h: 0.25,
    fontSize: 10, fontFace: FT, color: C.muted, margin: 0, charSpacing: 1,
  });
  slide.addText(`${String(n).padStart(2, "0")}  /  ${String(TOTAL).padStart(2, "0")}`, {
    x: 11.2, y: 7.12, w: 1.7, h: 0.25,
    fontSize: 10, fontFace: FT, color: C.cyan, align: "right", margin: 0,
  });
}

function pill(slide, x, y, w, h, text) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: C.panel },
    line: { color: C.cyanDim, width: 1 },
    rectRadius: 0.08,
  });
  slide.addText(text, {
    x, y, w, h,
    fontSize: 11, fontFace: FT, color: C.cyan, align: "center", valign: "middle",
    margin: 0, bold: true,
  });
}

function card(slide, x, y, w, h) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: C.panel },
    line: { color: C.line, width: 1 },
    rectRadius: 0.1,
  });
}

function sectionTitle(slide, chapter, title, subtitle) {
  darkBg(slide);
  slide.addText(chapter, {
    x: 0.6, y: 2.4, w: 12, h: 0.4,
    fontSize: 14, fontFace: FT, color: C.cyan, bold: true, charSpacing: 4, margin: 0,
  });
  slide.addText(title, {
    x: 0.6, y: 3.0, w: 12, h: 0.8,
    fontSize: 40, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  slide.addText(subtitle, {
    x: 0.6, y: 3.95, w: 11, h: 0.5,
    fontSize: 16, fontFace: FB, color: C.soft, margin: 0,
  });
}

// ===================== 1 Title =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addShape(pres.shapes.OVAL, {
    x: 9.8, y: -1.2, w: 5, h: 5,
    fill: { color: C.cyanDim, transparency: 88 },
    line: { color: C.void, transparency: 100 },
  });
  s.addShape(pres.shapes.OVAL, {
    x: -1.5, y: 4.5, w: 4, h: 4,
    fill: { color: C.mint, transparency: 92 },
    line: { color: C.void, transparency: 100 },
  });
  s.addText("LINGXI KNOWLEDGE OS", {
    x: 0.7, y: 1.7, w: 11, h: 0.35,
    fontSize: 13, fontFace: FT, color: C.cyan, bold: true, charSpacing: 5, margin: 0,
  });
  s.addText("面向设备手册的多模态\n多路融合检索智能问答系统", {
    x: 0.7, y: 2.2, w: 11.5, h: 1.7,
    fontSize: 36, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText("双 LangGraph 状态机  ·  BGE-M3 混合检索  ·  产品实体全链路约束  ·  工程闭环", {
    x: 0.7, y: 4.15, w: 11.5, h: 0.4,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
  });
  ["Dual Graph", "Hybrid Dense+Sparse", "Item-Name Guard", "Multimodal", "Multi-Recall"].forEach((t, i) => {
    pill(s, 0.7 + i * 2.35, 5.0, 2.2, 0.42, t);
  });
  footer(s, 1);
}

// ===================== 2 TOC =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("CONTENTS", {
    x: 0.7, y: 0.45, w: 4, h: 0.3,
    fontSize: 12, fontFace: FT, color: C.cyan, bold: true, charSpacing: 3, margin: 0,
  });
  s.addText("目录", {
    x: 0.7, y: 0.8, w: 6, h: 0.6,
    fontSize: 36, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const items = [
    ["01", "项目背景与业务价值", "手册痛点 · 垂直场景价值"],
    ["02", "系统整体架构", "双服务 · 数据平面 · 可观测"],
    ["03", "六大核心技术支柱", "双图 · 混合检索 · 实体 · 多模态 · 多路 · 闭环"],
    ["04", "双流水线设计", "导入状态机 · 查询状态机"],
    ["05", "演进与总结", "债务 · 路线图 · 收束"],
  ];
  items.forEach((it, i) => {
    const y = 1.7 + i * 0.95;
    card(s, 0.7, y, 11.9, 0.82);
    s.addText(it[0], {
      x: 0.95, y: y + 0.18, w: 1.1, h: 0.5,
      fontSize: 24, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(it[1], {
      x: 2.3, y: y + 0.12, w: 7, h: 0.35,
      fontSize: 18, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(it[2], {
      x: 2.3, y: y + 0.45, w: 9, h: 0.28,
      fontSize: 13, fontFace: FB, color: C.muted, margin: 0,
    });
  });
  footer(s, 2);
}

// ===================== 3 Chapter 01 =====================
{
  const s = pres.addSlide();
  sectionTitle(s, "CHAPTER  01", "项目背景与业务价值", "直击设备手册查阅痛点，重塑垂直场景知识检索体验");
  footer(s, 3);
}

// ===================== 4 Pain points =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PAIN POINTS", {
    x: 0.6, y: 0.35, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("设备手册查阅的四大核心痛点", {
    x: 0.6, y: 0.65, w: 12, h: 0.5,
    fontSize: 28, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText("多版本杂乱、跨型号串答、图纸信息丢失、专有词召回弱——单次检索问答难以破局。", {
    x: 0.6, y: 1.2, w: 12, h: 0.35,
    fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
  });
  const pains = [
    ["高成本", "版本杂乱 · 查阅极慢", "数十份 PDF 散落，新人找参数需翻数十页，培训与上手成本居高不下"],
    ["串答风险", "跨型号参数混淆", "同系列仅后缀不同，纯向量检索易召回错误型号步骤与参数"],
    ["多模态缺失", "图纸信息丢失", "接线图 / 爆炸图在纯文本 RAG 中被丢弃，图意无法进入检索"],
    ["语义漂移", "专有名词召回弱", "零件号、故障码在稠密空间易漂，精确编码命中率低"],
  ];
  pains.forEach((p, i) => {
    const x = 0.55 + (i % 2) * 6.35;
    const y = 1.75 + Math.floor(i / 2) * 2.4;
    card(s, x, y, 6.05, 2.15);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.12, h: 2.15, fill: { color: C.cyan },
    });
    s.addText(p[0], {
      x: x + 0.4, y: y + 0.25, w: 5.3, h: 0.3,
      fontSize: 12, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(p[1], {
      x: x + 0.4, y: y + 0.6, w: 5.3, h: 0.4,
      fontSize: 20, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(p[2], {
      x: x + 0.4, y: y + 1.15, w: 5.3, h: 0.7,
      fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  footer(s, 4);
}

// ===================== 5 Value =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("VALUE", {
    x: 0.6, y: 0.35, w: 3, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("输入范围与核心业务价值", {
    x: 0.6, y: 0.65, w: 12, h: 0.45,
    fontSize: 28, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const vals = [
    ["多格式入库", "PDF / MD / TXT / DOCX / PPTX", "MinerU + Office 转 MD，覆盖手册与通告"],
    ["图文联合", "VL 摘要 + MinIO URL", "插图语义回写切片，问答可附可点开配图"],
    ["效率跃升", "翻页 → 对话秒级定位", "运维 / 售后按型号问步骤与注意点"],
    ["可溯源边界", "以说明书为准", "检索增强生成，降低纯幻觉风险"],
  ];
  vals.forEach((v, i) => {
    const x = 0.55 + i * 3.15;
    card(s, x, 1.5, 3.0, 4.8);
    s.addShape(pres.shapes.OVAL, {
      x: x + 1.05, y: 1.85, w: 0.9, h: 0.9,
      fill: { color: C.deep },
      line: { color: C.cyan, width: 1.5 },
    });
    s.addText(String(i + 1).padStart(2, "0"), {
      x: x + 1.05, y: 1.85, w: 0.9, h: 0.9,
      fontSize: 16, fontFace: FT, color: C.cyan, align: "center", valign: "middle", bold: true, margin: 0,
    });
    s.addText(v[0], {
      x: x + 0.2, y: 3.05, w: 2.6, h: 0.5,
      fontSize: 18, fontFace: FT, color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addText(v[1], {
      x: x + 0.2, y: 3.6, w: 2.6, h: 0.7,
      fontSize: 13, fontFace: FT, color: C.cyan, align: "center", margin: 0,
    });
    s.addText(v[2], {
      x: x + 0.25, y: 4.5, w: 2.5, h: 1.2,
      fontSize: 13, fontFace: FB, color: C.soft, align: "center", margin: 0,
    });
  });
  footer(s, 5);
}

// ===================== 6 Chapter 02 =====================
{
  const s = pres.addSlide();
  sectionTitle(s, "CHAPTER  02", "系统整体架构与数据平面", "双服务解耦 · 共享底座 · 生产级可观测");
  footer(s, 6);
}

// ===================== 7 Architecture =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("ARCHITECTURE", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("双 LangGraph 状态机架构总览", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 26, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText("不是「一问一搜」：导入与查询各自是可观测状态机，共享 clients / lm，经 Milvus 间接衔接。", {
    x: 0.6, y: 1.05, w: 12, h: 0.35,
    fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
  });

  // two columns
  card(s, 0.5, 1.55, 6.0, 4.9);
  card(s, 6.8, 1.55, 6.0, 4.9);
  s.addText("IMPORT  :8000", {
    x: 0.75, y: 1.75, w: 5.5, h: 0.35,
    fontSize: 14, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("kb_import_app", {
    x: 0.75, y: 2.15, w: 5.5, h: 0.35,
    fontSize: 20, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText([
    { text: "上传 → 解析 → 切分 → 向量 → 入库", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "· 节点级进度 / status 轮询", options: { breakLine: true } },
    { text: "· MinerU / VL / BGE-M3", options: { breakLine: true } },
    { text: "· 写 kb_item_names_v2 + kb_chunks_v2", options: { breakLine: true } },
    { text: "· MinIO 原稿与配图 URL", options: { breakLine: true } },
  ], {
    x: 0.75, y: 2.7, w: 5.5, h: 3.3,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
  });

  s.addText("QUERY  :8001", {
    x: 7.05, y: 1.75, w: 5.5, h: 0.35,
    fontSize: 14, fontFace: FT, color: C.mint, bold: true, margin: 0,
  });
  s.addText("query_app", {
    x: 7.05, y: 2.15, w: 5.5, h: 0.35,
    fontSize: 20, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText([
    { text: "确认产品 → 多路检索 → 融合 → 重排 → 生成", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "· SSE 流式答案与阶段进度", options: { breakLine: true } },
    { text: "· 反问短路 / 型号过滤", options: { breakLine: true } },
    { text: "· Embedding · HyDE · Web MCP · KG桩", options: { breakLine: true } },
    { text: "· Mongo 会话历史", options: { breakLine: true } },
  ], {
    x: 7.05, y: 2.7, w: 5.5, h: 3.3,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
  });
  footer(s, 7);
}

// ===================== 8 Data plane =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("DATA PLANE", {
    x: 0.6, y: 0.35, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("双服务边界与分层数据平面", {
    x: 0.6, y: 0.65, w: 12, h: 0.45,
    fontSize: 26, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const planes = [
    ["Milvus", "向量知识底座", "kb_chunks_v2 切片\nkb_item_names_v2 型号\ndense + sparse 双索引"],
    ["MinIO", "对象与配图", "原稿归档\nMD 图片公网 URL\n匿名只读访问"],
    ["MongoDB", "会话记忆", "chat_message\n多轮上下文\n改写与 item_names"],
    ["内存任务态", "可观测进度", "task_utils 节点列表\n导入轮询 / 查询 SSE\n进程内（演进 Redis）"],
  ];
  planes.forEach((p, i) => {
    const x = 0.5 + i * 3.2;
    card(s, x, 1.5, 3.0, 4.9);
    s.addText(p[0], {
      x: x + 0.2, y: 1.8, w: 2.6, h: 0.4,
      fontSize: 14, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(p[1], {
      x: x + 0.2, y: 2.35, w: 2.6, h: 0.55,
      fontSize: 20, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(p[2], {
      x: x + 0.2, y: 3.2, w: 2.6, h: 2.8,
      fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  footer(s, 8);
}

// ===================== 9 Chapter 03 pillars =====================
{
  const s = pres.addSlide();
  sectionTitle(s, "CHAPTER  03", "六大核心技术支柱", "从「单次检索问答」升级为可编排、可融合、可闭环的生产检索架构");
  footer(s, 9);
}

// ===================== 10 Six pillars overview =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("CORE PILLARS", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("核心技术：不止于单次检索问答", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 26, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const pillars = [
    ["01", "双图编排", "导入 / 查询各自 LangGraph 状态机，节点可观测可分支"],
    ["02", "混合检索", "BGE-M3 dense+sparse，适配型号与配件等专有词"],
    ["03", "主体名贯穿", "导入抽 item_name，查询先确认产品，抑制串答"],
    ["04", "多模态处理", "MinerU→MD，VL 摘要图意，MinIO URL 回写"],
    ["05", "多路再融合", "向量 / HyDE / 联网 / 图谱桩 → join · RRF · rerank"],
    ["06", "工程闭环", "MinIO · Milvus · Mongo · SSE，完整读写闭环"],
  ];
  pillars.forEach((p, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.5 + col * 4.2;
    const y = 1.3 + row * 2.7;
    card(s, x, y, 4.0, 2.45);
    s.addText(p[0], {
      x: x + 0.25, y: y + 0.3, w: 1.2, h: 0.4,
      fontSize: 22, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(p[1], {
      x: x + 0.25, y: y + 0.85, w: 3.5, h: 0.4,
      fontSize: 20, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(p[2], {
      x: x + 0.25, y: y + 1.4, w: 3.5, h: 0.8,
      fontSize: 13, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  footer(s, 10);
}

// ===================== 11 Dual graph detail =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PILLAR 01", {
    x: 0.6, y: 0.3, w: 3, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("双图编排：状态机而非黑盒流水线", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  // import pipeline chips
  s.addText("导入图  kb_import_app", {
    x: 0.6, y: 1.2, w: 12, h: 0.35,
    fontSize: 14, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  const stepsIn = ["入口", "PDF/Office→MD", "图摘要", "切分", "识别型号", "BGE", "入库"];
  stepsIn.forEach((t, i) => {
    const x = 0.55 + i * 1.8;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 1.65, w: 1.65, h: 0.55,
      fill: { color: C.panel2 },
      line: { color: C.cyanDim, width: 1 },
      rectRadius: 0.08,
    });
    s.addText(t, {
      x, y: 1.65, w: 1.65, h: 0.55,
      fontSize: 12, fontFace: FT, color: C.ice, align: "center", valign: "middle", margin: 0, bold: true,
    });
    if (i < stepsIn.length - 1) {
      s.addShape(pres.shapes.RIGHT_ARROW, {
        x: x + 1.62, y: 1.82, w: 0.2, h: 0.2,
        fill: { color: C.cyanDim },
      });
    }
  });

  s.addText("查询图  query_app", {
    x: 0.6, y: 2.55, w: 12, h: 0.35,
    fontSize: 14, fontFace: FT, color: C.mint, bold: true, margin: 0,
  });
  const stepsQ = ["确认产品", "多路扇出", "join", "RRF", "重排", "生成"];
  stepsQ.forEach((t, i) => {
    const x = 0.55 + i * 2.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y: 3.0, w: 1.9, h: 0.55,
      fill: { color: C.panel2 },
      line: { color: "0D9488", width: 1 },
      rectRadius: 0.08,
    });
    s.addText(t, {
      x, y: 3.0, w: 1.9, h: 0.55,
      fontSize: 13, fontFace: FT, color: C.ice, align: "center", valign: "middle", margin: 0, bold: true,
    });
  });

  card(s, 0.55, 3.9, 12.2, 2.55);
  s.addText("可观测价值", {
    x: 0.85, y: 4.15, w: 11.5, h: 0.35,
    fontSize: 16, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText([
    { text: "· 每个节点写入 running / done，导入页轮询、问答页 SSE 实时展示阶段，告别黑盒批处理。", options: { breakLine: true } },
    { text: "· 条件边：PDF/MD 分支、商品多候选反问短路——流程可分支，而非固定单次检索。", options: { breakLine: true } },
    { text: "· 两图不互相 invoke：通过 item_name + Milvus 衔接，职责清晰、可独立扩缩。", options: { breakLine: true } },
  ], {
    x: 0.85, y: 4.6, w: 11.5, h: 1.6,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
  });
  footer(s, 11);
}

// ===================== 12 Hybrid =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PILLAR 02", {
    x: 0.6, y: 0.3, w: 3, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("混合检索：dense + sparse，而不是只做稠密", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const hyb = [
    ["Dense", "语义相似", "COSINE / IVF_FLAT\n说法不同也能近"],
    ["Sparse", "关键词敏感", "IP / 倒排稀疏\n型号·配件·故障码"],
    ["Hybrid", "加权融合", "WeightedRanker\n常用 0.8 / 0.2"],
    ["再精排", "RRF → Rerank", "多路名次融合\n问题-段落打分"],
  ];
  hyb.forEach((h, i) => {
    const x = 0.5 + i * 3.2;
    card(s, x, 1.35, 3.05, 3.4);
    s.addText(h[0], {
      x: x + 0.2, y: 1.6, w: 2.65, h: 0.4,
      fontSize: 14, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(h[1], {
      x: x + 0.2, y: 2.15, w: 2.65, h: 0.5,
      fontSize: 20, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(h[2], {
      x: x + 0.2, y: 2.9, w: 2.65, h: 1.5,
      fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  s.addText("适配设备手册：专有词要「咬死」，同义问法要「听懂」——双通道同时满足。", {
    x: 0.6, y: 5.05, w: 12, h: 0.4,
    fontSize: 15, fontFace: FB, color: C.ice, margin: 0,
  });
  card(s, 0.5, 5.55, 12.3, 1.2);
  s.addText("实现锚点：embedding_utils.generate_embeddings → milvus_utils.create_hybrid_search_requests + hybrid_search（商品名确认与切片检索同构）", {
    x: 0.8, y: 5.8, w: 11.8, h: 0.7,
    fontSize: 14, fontFace: FB, color: C.soft, margin: 0, valign: "middle",
  });
  footer(s, 12);
}

// ===================== 13 Item name =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PILLAR 03", {
    x: 0.6, y: 0.3, w: 3, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("产品 / 主体名识别贯穿全链路", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  // flow
  const flow = [
    ["导入", "LLM 抽 item_name\n回填每个 chunk\n写入商品名集合"],
    ["主键", "同名幂等覆盖\n切片元数据打标\n向量拼接前置商品名"],
    ["查询", "历史+LLM 抽型号\n混合检索对齐标准名\n高分确认 / 中分反问"],
    ["过滤", "item_name in [...]\n物理隔离跨型号\n再进入多路检索"],
  ];
  flow.forEach((f, i) => {
    const x = 0.5 + i * 3.2;
    card(s, x, 1.3, 3.05, 3.6);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: x + 0.7, y: 1.55, w: 1.65, h: 0.45,
      fill: { color: C.deep },
      line: { color: C.cyan, width: 1 },
      rectRadius: 0.08,
    });
    s.addText(f[0], {
      x: x + 0.7, y: 1.55, w: 1.65, h: 0.45,
      fontSize: 14, fontFace: FT, color: C.cyan, align: "center", valign: "middle", bold: true, margin: 0,
    });
    s.addText(f[1], {
      x: x + 0.25, y: 2.3, w: 2.55, h: 2.3,
      fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  s.addText("垂直场景关键设计：先锁定「问的是哪款设备」，再谈检索与生成，从源头减少串答。", {
    x: 0.6, y: 5.2, w: 12, h: 0.4,
    fontSize: 15, fontFace: FB, color: C.ice, margin: 0,
  });
  card(s, 0.5, 5.75, 12.3, 1.0);
  s.addText("反问示例：「您是想问以下哪个产品：A、B、C？请明确型号。」→ 本轮短路至答案输出，不盲目检索。", {
    x: 0.8, y: 5.95, w: 11.8, h: 0.6,
    fontSize: 14, fontFace: FB, color: C.soft, margin: 0, valign: "middle",
  });
  footer(s, 13);
}

// ===================== 14 Multimodal + multi-recall =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PILLAR 04 · 05", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("多模态文档处理  ×  多路召回再融合", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });

  card(s, 0.5, 1.25, 6.0, 5.2);
  s.addText("多模态", {
    x: 0.8, y: 1.5, w: 5.4, h: 0.4,
    fontSize: 18, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText([
    { text: "1. PDF → MinerU → Markdown（保留结构）", options: { breakLine: true } },
    { text: "2. 扫描 images/ 中被引用的插图", options: { breakLine: true } },
    { text: "3. VL 生成短摘要（图意进入文本）", options: { breakLine: true } },
    { text: "4. 上传 MinIO，MD 改写为公网 URL", options: { breakLine: true } },
    { text: "5. 切分入库后，问答可附说明书配图", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "结果：检索时文本与图意都能用上，不再「只认字、看不见图」。", options: { breakLine: false } },
  ], {
    x: 0.8, y: 2.15, w: 5.4, h: 3.9,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
  });

  card(s, 6.8, 1.25, 6.0, 5.2);
  s.addText("多路融合", {
    x: 7.1, y: 1.5, w: 5.4, h: 0.4,
    fontSize: 18, fontFace: FT, color: C.mint, bold: true, margin: 0,
  });
  s.addText([
    { text: "并行四路：", options: { breakLine: true, bold: true } },
    { text: "· Embedding 原生向量检索", options: { breakLine: true } },
    { text: "· HyDE 假设性文档检索", options: { breakLine: true } },
    { text: "· WebSearch MCP 联网兜底", options: { breakLine: true } },
    { text: "· Knowledge Graph（当前占位）", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "融合：join → RRF（向量+HyDE）→ Rerank（+联网）→ LLM", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "比「一问一搜」更接近生产级检索架构。", options: { breakLine: false } },
  ], {
    x: 7.1, y: 2.15, w: 5.4, h: 3.9,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0,
  });
  footer(s, 14);
}

// ===================== 15 Engineering loop =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PILLAR 06", {
    x: 0.6, y: 0.3, w: 3, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, margin: 0,
  });
  s.addText("工程闭环相对完整", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const loop = [
    ["MinIO", "原件 · 配图", "对象持久化\nURL 可访问"],
    ["Milvus", "知识向量", "型号 + 切片\n混合检索"],
    ["Mongo", "会话状态", "多轮历史\n改写与标注"],
    ["SSE / 轮询", "交互反馈", "流式答案\n节点进度"],
  ];
  loop.forEach((l, i) => {
    const x = 0.55 + i * 3.2;
    card(s, x, 1.4, 3.05, 3.5);
    s.addText((i + 1).toString().padStart(2, "0"), {
      x: x + 0.25, y: 1.65, w: 2.5, h: 0.35,
      fontSize: 14, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(l[0], {
      x: x + 0.25, y: 2.15, w: 2.5, h: 0.45,
      fontSize: 22, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(l[1], {
      x: x + 0.25, y: 2.7, w: 2.5, h: 0.4,
      fontSize: 14, fontFace: FT, color: C.mint, margin: 0,
    });
    s.addText(l[2], {
      x: x + 0.25, y: 3.3, w: 2.5, h: 1.2,
      fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  card(s, 0.55, 5.2, 12.2, 1.45);
  s.addText("闭环含义：文档进得去（导入可观测）、知识找得到（混合+多路）、答案讲得清（重排+流式）、过程看得见（进度与历史）——形成可演示、可迭代的完整产品形态。", {
    x: 0.85, y: 5.45, w: 11.6, h: 1.0,
    fontSize: 15, fontFace: FB, color: C.soft, margin: 0, valign: "middle",
  });
  footer(s, 15);
}

// ===================== 16 Chapter 04 =====================
{
  const s = pres.addSlide();
  sectionTitle(
    s,
    "CHAPTER  04",
    "双流水线核心设计",
    "从非结构化文档到精准答案：导入状态机写库 · 查询状态机读库"
  );
  footer(s, 16);
}

// ===================== 17 Import pipeline =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PIPELINE A", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("导入流水线：多模态解析 → 结构化入库", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText("六步标准化节点 + 任务进度可观测，把手册变成可检索的双向量知识。", {
    x: 0.6, y: 1.05, w: 12, h: 0.3,
    fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
  });
  const steps = [
    ["01", "入口与格式", "校验扩展名；PDF / MD 直通；TXT·DOCX·PPTX 转 MD；旧版 Office 明确失败"],
    ["02", "PDF→MD", "MinerU 云解析：申请 URL → 上传 → 轮询 → ZIP → 抽出 Markdown"],
    ["03", "媒体处理", "VL 为插图写摘要；上传 MinIO；MD 内链改写为公网 URL"],
    ["04", "文档切分", "按标题初切；超长再切；过短合并；产出 chunks[]"],
    ["05", "主体识别", "LLM 抽 item_name；回填切片；写入 kb_item_names_v2"],
    ["06", "向量入库", "BGE-M3 dense+sparse；按型号幂等清理；写入 kb_chunks_v2"],
  ];
  steps.forEach((st, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.5 + col * 4.2;
    const y = 1.5 + row * 2.55;
    card(s, x, y, 4.0, 2.35);
    s.addText(st[0], {
      x: x + 0.25, y: y + 0.25, w: 1.2, h: 0.35,
      fontSize: 18, fontFace: FT, color: C.cyan, bold: true, margin: 0,
    });
    s.addText(st[1], {
      x: x + 0.25, y: y + 0.7, w: 3.5, h: 0.4,
      fontSize: 18, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(st[2], {
      x: x + 0.25, y: y + 1.2, w: 3.5, h: 0.9,
      fontSize: 13, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  footer(s, 17);
}

// ===================== 18 Query pipeline =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("PIPELINE B", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.mint, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("查询流水线：确认产品 → 多路召回 → 融合生成", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText("以商品实体为守门员，四路并行后 RRF / Rerank，SSE 流式输出可溯源答案。", {
    x: 0.6, y: 1.05, w: 12, h: 0.3,
    fontSize: 14, fontFace: FB, color: C.soft, margin: 0,
  });
  const qsteps = [
    ["01", "实体确认", "Mongo 历史 + LLM 抽型号；对齐 kb_item_names_v2；多候选反问短路"],
    ["02", "四路扇出", "Embedding · HyDE · Web MCP · KG 占位，最大化召回覆盖"],
    ["03", "融合重排", "RRF 合并向量/HyDE；Rerank 并入联网结果并动态 TopK"],
    ["04", "生成溯源", "LLM 作答；说明书优先；SSE 推送；历史写入 Mongo"],
  ];
  qsteps.forEach((st, i) => {
    const x = 0.5 + i * 3.2;
    card(s, x, 1.55, 3.05, 4.85);
    s.addShape(pres.shapes.OVAL, {
      x: x + 1.0, y: 1.85, w: 0.95, h: 0.95,
      fill: { color: C.deep },
      line: { color: C.mint, width: 1.5 },
    });
    s.addText(st[0], {
      x: x + 1.0, y: 1.85, w: 0.95, h: 0.95,
      fontSize: 16, fontFace: FT, color: C.mint, align: "center", valign: "middle", bold: true, margin: 0,
    });
    s.addText(st[1], {
      x: x + 0.2, y: 3.1, w: 2.65, h: 0.5,
      fontSize: 18, fontFace: FT, color: C.white, bold: true, align: "center", margin: 0,
    });
    s.addText(st[2], {
      x: x + 0.25, y: 3.8, w: 2.55, h: 2.2,
      fontSize: 14, fontFace: FB, color: C.soft, align: "center", margin: 0,
    });
  });
  footer(s, 18);
}

// ===================== 19 Chapter 05 =====================
{
  const s = pres.addSlide();
  sectionTitle(
    s,
    "CHAPTER  05",
    "演进与总结",
    "正视架构债务 · 规划 V2.0 · 收束核心价值"
  );
  footer(s, 19);
}

// ===================== 20 Debt =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("TECH DEBT", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.warn, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("当前架构债务与薄弱点", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const debts = [
    ["高", "任务状态纯内存", "task_utils 不跨进程；重启丢失；难多 Worker"],
    ["高", "图谱一路为空桩", "node_query_kg / Neo4j 未落地，四路实为三路"],
    ["中", "无统一鉴权网关", "CORS *；密钥集中 .env；缺限流熔断"],
    ["中", "历史工具重复", "mongo_history_utils 新旧并存，维护分叉"],
    ["低", "切分开关未接线", "silicon / vllm / advanced 配置基本死代码"],
    ["低", "MinIO 失败仅警告", "原稿上传失败仍继续本地图，需强一致策略"],
  ];
  debts.forEach((d, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.5 + col * 4.2;
    const y = 1.25 + row * 2.7;
    card(s, x, y, 4.0, 2.45);
    const tone = d[0] === "高" ? C.rose : d[0] === "中" ? C.warn : C.cyan;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: x + 0.25, y: y + 0.3, w: 0.7, h: 0.35,
      fill: { color: C.deep },
      line: { color: tone, width: 1 },
      rectRadius: 0.06,
    });
    s.addText(d[0], {
      x: x + 0.25, y: y + 0.3, w: 0.7, h: 0.35,
      fontSize: 12, fontFace: FT, color: tone, align: "center", valign: "middle", bold: true, margin: 0,
    });
    s.addText(d[1], {
      x: x + 0.25, y: y + 0.85, w: 3.5, h: 0.45,
      fontSize: 17, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(d[2], {
      x: x + 0.25, y: y + 1.4, w: 3.5, h: 0.8,
      fontSize: 13, fontFace: FB, color: C.soft, margin: 0,
    });
  });
  footer(s, 20);
}

// ===================== 21 Roadmap =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addText("ROADMAP V2.0", {
    x: 0.6, y: 0.3, w: 4, h: 0.25,
    fontSize: 11, fontFace: FT, color: C.cyan, bold: true, charSpacing: 2, margin: 0,
  });
  s.addText("架构演进与优化路线图", {
    x: 0.6, y: 0.55, w: 12, h: 0.45,
    fontSize: 24, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  const roads = [
    ["01", "状态持久化", "Redis 替换进程内字典", "跨进程共享 · 多 Worker · 重启可恢复"],
    ["02", "图谱链路", "Neo4j 业务真正接入", "补齐第四路 · BOM/故障关系增强召回"],
    ["03", "安全网关", "统一鉴权与限流", "OAuth2/JWT · CORS 收敛 · 熔断"],
    ["04", "存储一致", "合并历史工具 + MinIO 重试", "强校验上传 · 减少冗余实现"],
  ];
  roads.forEach((r, i) => {
    const y = 1.25 + i * 1.3;
    card(s, 0.55, y, 12.2, 1.15);
    s.addText(r[0], {
      x: 0.8, y: y + 0.3, w: 0.9, h: 0.55,
      fontSize: 22, fontFace: FT, color: C.cyan, bold: true, margin: 0, valign: "middle",
    });
    s.addText(r[1], {
      x: 1.9, y: y + 0.2, w: 3.2, h: 0.35,
      fontSize: 16, fontFace: FT, color: C.white, bold: true, margin: 0,
    });
    s.addText(r[2], {
      x: 1.9, y: y + 0.55, w: 4.5, h: 0.35,
      fontSize: 13, fontFace: FB, color: C.mint, margin: 0,
    });
    s.addText(r[3], {
      x: 6.8, y: y + 0.3, w: 5.6, h: 0.55,
      fontSize: 14, fontFace: FB, color: C.soft, margin: 0, valign: "middle",
    });
  });
  footer(s, 21);
}

// ===================== 22 Summary + Thanks =====================
{
  const s = pres.addSlide();
  darkBg(s);
  s.addShape(pres.shapes.OVAL, {
    x: 9.5, y: -0.8, w: 5.5, h: 5.5,
    fill: { color: C.cyanDim, transparency: 90 },
    line: { color: C.void, transparency: 100 },
  });
  s.addText("SUMMARY", {
    x: 0.7, y: 1.35, w: 12, h: 0.3,
    fontSize: 12, fontFace: FT, color: C.cyan, bold: true, charSpacing: 4, margin: 0,
  });
  s.addText("总结", {
    x: 0.7, y: 1.75, w: 12, h: 0.6,
    fontSize: 36, fontFace: FT, color: C.white, bold: true, margin: 0,
  });
  s.addText([
    { text: "以双 LangGraph 编排导入与查询，而不是单次黑盒检索。", options: { breakLine: true } },
    { text: "以 dense+sparse 混合检索 + 多路融合，守住型号与专有词精度。", options: { breakLine: true } },
    { text: "以 item_name 贯穿链路，抑制跨型号串答。", options: { breakLine: true } },
    { text: "以多模态与工程闭环，让手册「进得去、找得到、答得清、看得见」。", options: { breakLine: true } },
  ], {
    x: 0.7, y: 2.55, w: 11.5, h: 2.2,
    fontSize: 16, fontFace: FB, color: C.soft, margin: 0,
  });
  s.addText("感谢聆听  ·  让设备手册知识检索更精准、更可靠、更可观测", {
    x: 0.7, y: 5.1, w: 12, h: 0.45,
    fontSize: 16, fontFace: FT, color: C.ice, margin: 0,
  });
  footer(s, 22);
}

const out = path.join(
  __dirname,
  "面向设备手册的多模态多路融合检索智能问答系统-1021.pptx"
);
pres.writeFile({ fileName: out }).then(() => {
  console.log("Wrote", out);
}).catch((e) => {
  console.error(e);
  process.exit(1);
});
