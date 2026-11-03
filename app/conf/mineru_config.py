# 导入核心依赖：数据类、环境变量读取、路径处理
from dataclasses import dataclass
import os
import warnings
from dotenv import load_dotenv

# 提前加载.env配置文件（必须在读取环境变量前执行，确保os.getenv能获取到值）
load_dotenv()

# MinerU 云端硬上限（页）
MINERU_HARD_PAGE_LIMIT = 200


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        warnings.warn(f"[MineruConfig] {name}={raw!r} 非法，使用默认值 {default}")
        return default


# 定义minerU服务配置
@dataclass
class MineruConfig:
    base_url: str
    api_key: str
    max_pages: int = 180
    split_concurrency: int = 2
    part_retries: int = 2


def _build_mineru_config() -> MineruConfig:
    max_pages = _env_int("MINERU_MAX_PAGES", 180)
    if max_pages < 1:
        max_pages = 1
    if max_pages > MINERU_HARD_PAGE_LIMIT:
        warnings.warn(
            f"[MineruConfig] MINERU_MAX_PAGES={max_pages} 超过云端硬上限 "
            f"{MINERU_HARD_PAGE_LIMIT}，已 clamp 为 {MINERU_HARD_PAGE_LIMIT}"
        )
        max_pages = MINERU_HARD_PAGE_LIMIT

    concurrency = max(1, _env_int("MINERU_SPLIT_CONCURRENCY", 2))
    retries = max(0, _env_int("MINERU_PART_RETRIES", 2))

    return MineruConfig(
        base_url=os.getenv("MINERU_BASE_URL"),
        api_key=os.getenv("MINERU_API_TOKEN"),
        max_pages=max_pages,
        split_concurrency=concurrency,
        part_retries=retries,
    )


mineru_config = _build_mineru_config()
