from pathlib import Path

cache_dir = Path(__file__).parent / ".cache"  # 缓存目录
cache_dir.mkdir(exist_ok=True, parents=True)
