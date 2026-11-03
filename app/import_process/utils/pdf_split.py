"""PDF 按页拆分与多段 Markdown/图片合并（供 MinerU 超页导入使用）。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import fitz

from app.core.logger import logger


def compute_page_ranges(total_pages: int, max_pages: int) -> list[tuple[int, int]]:
    """按 max_pages 切分为 1-based 闭区间页窗列表。"""
    if total_pages < 1:
        raise ValueError(f"total_pages 必须 >= 1，当前：{total_pages}")
    if max_pages < 1:
        raise ValueError(f"max_pages 必须 >= 1，当前：{max_pages}")
    ranges: list[tuple[int, int]] = []
    start = 1
    while start <= total_pages:
        end = min(start + max_pages - 1, total_pages)
        ranges.append((start, end))
        start = end + 1
    return ranges


def split_pdf_by_pages(
    pdf_path: Path,
    out_dir: Path,
    max_pages: int,
) -> list[tuple[Path, int, int]]:
    """
    将 PDF 按页窗拆成多个文件。
    返回 [(part_path, page_start, page_end), ...]，页码 1-based。
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = fitz.open(pdf_path)
    try:
        total = src.page_count
        ranges = compute_page_ranges(total, max_pages)
        stem = pdf_path.stem
        results: list[tuple[Path, int, int]] = []
        for start, end in ranges:
            part_name = f"{stem}_p{start}-{end}.pdf"
            part_path = out_dir / part_name
            part_doc = fitz.open()
            try:
                # fitz 页码 0-based；insert_pdf 的 to_page 为 inclusive
                part_doc.insert_pdf(src, from_page=start - 1, to_page=end - 1)
                part_doc.save(part_path)
            finally:
                part_doc.close()
            results.append((part_path, start, end))
            logger.info(f"[pdf_split] 写出分段 {part_name}（页 {start}-{end}/{total}）")
        return results
    finally:
        src.close()


def rewrite_image_refs(md: str, rename_map: dict[str, str]) -> str:
    """将 MD 中的图片文件名按 rename_map 改写（仅替换路径末尾文件名）。"""
    if not rename_map:
        return md

    def _repl(match: re.Match[str]) -> str:
        prefix, fname, suffix = match.group(1), match.group(2), match.group(3)
        new_name = rename_map.get(fname, fname)
        return f"{prefix}{new_name}{suffix}"

    # 匹配 ](.../images/xxx.ext) 或 ](images/xxx.ext)
    pattern = re.compile(
        r"(\]\(\s*(?:\./)?(?:images/))"
        r"([^)/\s]+)"
        r"(\s*\))"
    )
    return pattern.sub(_repl, md)


def _find_md_in_dir(part_dir: Path) -> Path:
    md_files = list(part_dir.rglob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"分段目录中未找到 MD：{part_dir}")
    for md in md_files:
        if md.name.lower() == "full.md":
            return md
    for md in md_files:
        if md.parent == part_dir or md.parent.name == part_dir.name:
            return md
    return md_files[0]


def merge_part_markdowns(
    part_md_dirs: list[Path],
    final_dir: Path,
    stem: str,
    part_labels: list[str] | None = None,
) -> Path:
    """
    按顺序合并多段解析目录中的 MD 与 images/。
    图片重名时加 p{idx}_ 前缀并改写引用。
    返回最终 MD 绝对路径。
    """
    if not part_md_dirs:
        raise ValueError("part_md_dirs 不能为空")

    final_dir = Path(final_dir)
    images_dir = final_dir / "images"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    chunks: list[str] = []

    for idx, part_dir in enumerate(part_md_dirs):
        part_dir = Path(part_dir)
        md_path = _find_md_in_dir(part_dir)
        md_text = md_path.read_text(encoding="utf-8")

        # 图片目录：优先 md 同级 images，否则 part 下任意 images
        local_images = md_path.parent / "images"
        if not local_images.is_dir():
            found = list(part_dir.rglob("images"))
            local_images = next((p for p in found if p.is_dir()), None)

        rename_map: dict[str, str] = {}
        if local_images and local_images.is_dir():
            for img in sorted(local_images.iterdir()):
                if not img.is_file():
                    continue
                new_name = img.name
                if new_name in used_names:
                    new_name = f"p{idx}_{img.name}"
                # 极端情况仍冲突
                while new_name in used_names:
                    new_name = f"p{idx}_{new_name}"
                dest = images_dir / new_name
                shutil.copy2(img, dest)
                used_names.add(new_name)
                if new_name != img.name:
                    rename_map[img.name] = new_name

        md_text = rewrite_image_refs(md_text, rename_map)
        label = None
        if part_labels and idx < len(part_labels):
            label = part_labels[idx]
        if label:
            chunks.append(f"<!-- mineru-part: {label} -->\n\n{md_text.strip()}\n")
        else:
            chunks.append(md_text.strip() + "\n")

    final_md = final_dir / f"{stem}.md"
    final_md.write_text("\n".join(chunks), encoding="utf-8")
    logger.info(f"[pdf_split] 合并完成：{final_md}，图片数={len(used_names)}")
    return final_md.resolve()
