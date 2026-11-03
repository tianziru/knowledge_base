"""
将办公/纯文本文档转换为 Markdown，供导入图 MD 分支使用。
支持：.txt / .text / .docx / .pptx
不支持（明确报错）：.doc / .ppt（需另存为 docx/pptx）
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import FrozenSet

SUPPORTED_DIRECT_MD: FrozenSet[str] = frozenset({".md", ".markdown"})
SUPPORTED_PDF: FrozenSet[str] = frozenset({".pdf"})
SUPPORTED_TEXT: FrozenSet[str] = frozenset({".txt", ".text"})
SUPPORTED_DOCX: FrozenSet[str] = frozenset({".docx"})
SUPPORTED_PPTX: FrozenSet[str] = frozenset({".pptx"})
UNSUPPORTED_LEGACY: FrozenSet[str] = frozenset({".doc", ".ppt"})

# 上传/入口允许的全部扩展名
ALLOWED_UPLOAD_EXTS: FrozenSet[str] = (
    SUPPORTED_DIRECT_MD
    | SUPPORTED_PDF
    | SUPPORTED_TEXT
    | SUPPORTED_DOCX
    | SUPPORTED_PPTX
    | UNSUPPORTED_LEGACY
)

# 需要转为 MD 再走 MD 分支的扩展名
CONVERTIBLE_TO_MD: FrozenSet[str] = SUPPORTED_TEXT | SUPPORTED_DOCX | SUPPORTED_PPTX


def normalize_ext(path: str) -> str:
    return Path(path).suffix.lower()


def is_allowed_upload(filename: str) -> bool:
    return normalize_ext(filename) in ALLOWED_UPLOAD_EXTS


def _read_text_file(src: Path) -> str:
    raw = src.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _docx_to_markdown(src: Path) -> str:
    from docx import Document  # type: ignore

    doc = Document(str(src))
    parts: list[str] = []
    for para in doc.paragraphs:
        text = (para.text or "").rstrip()
        if text:
            parts.append(text)
    # 简单表格：逐行用 | 拼接
    for table in doc.tables:
        for row in table.rows:
            cells = [(c.text or "").strip().replace("\n", " ") for c in row.cells]
            if any(cells):
                parts.append("| " + " | ".join(cells) + " |")
        parts.append("")
    body = "\n\n".join(parts).strip()
    title = src.stem
    return f"# {title}\n\n{body}\n" if body else f"# {title}\n\n"


def _pptx_to_markdown(src: Path) -> str:
    from pptx import Presentation  # type: ignore

    prs = Presentation(str(src))
    parts: list[str] = [f"# {src.stem}", ""]
    for idx, slide in enumerate(prs.slides, start=1):
        parts.append(f"## 幻灯片 {idx}")
        parts.append("")
        texts: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    line = "".join(run.text for run in para.runs).strip()
                    if not line and para.text:
                        line = para.text.strip()
                    if line:
                        texts.append(line)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    cells = [(c.text or "").strip().replace("\n", " ") for c in row.cells]
                    if any(cells):
                        texts.append("| " + " | ".join(cells) + " |")
        if texts:
            parts.extend(texts)
            parts.append("")
        else:
            parts.append("（本页无文本）")
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def convert_to_md(src_path: str, dest_dir: str | None = None) -> str:
    """
    将可转换文档写成 Markdown 文件，返回生成的 .md 绝对路径。

    :raises ValueError: 不支持或转换失败
    """
    src = Path(src_path).resolve()
    if not src.is_file():
        raise ValueError(f"源文件不存在：{src}")

    ext = normalize_ext(str(src))
    if ext in UNSUPPORTED_LEGACY:
        raise ValueError(
            f"暂不支持旧版 Office 二进制格式（{ext}）。"
            f"请用 Word/PowerPoint 另存为 .docx / .pptx 后重新上传。"
        )
    if ext not in CONVERTIBLE_TO_MD:
        raise ValueError(f"无法转换为 Markdown 的格式：{ext}")

    out_dir = Path(dest_dir).resolve() if dest_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{src.stem}.converted.md"

    if ext in SUPPORTED_TEXT:
        body = _read_text_file(src)
        content = f"# {src.stem}\n\n{body.strip()}\n"
    elif ext in SUPPORTED_DOCX:
        content = _docx_to_markdown(src)
    else:
        content = _pptx_to_markdown(src)

    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def ensure_md_for_import(local_file_path: str, local_dir: str | None = None) -> tuple[str, str]:
    """
    根据扩展名决定导入路径类型。

    :return: (kind, path) kind in {"pdf", "md"}；path 为后续节点使用的文件路径
    """
    ext = normalize_ext(local_file_path)
    if ext in SUPPORTED_PDF:
        return "pdf", local_file_path
    if ext in SUPPORTED_DIRECT_MD:
        return "md", local_file_path
    if ext in CONVERTIBLE_TO_MD or ext in UNSUPPORTED_LEGACY:
        dest = local_dir or os.path.dirname(local_file_path)
        md_path = convert_to_md(local_file_path, dest)
        return "md", md_path
    raise ValueError(
        f"不支持的文件格式：{ext or '(无扩展名)'}。"
        f"支持：pdf / md / txt / docx / pptx"
    )
