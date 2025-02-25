from .models import CrawlResult, CacheMode, ExtractionOptions, CrawlTask
from .crawler import AsyncWebCrawler
from .extraction_strategy import ExtractionStrategy
from .config import DEFAULT_CRAWLER_CONFIG

__version__ = "0.1.0"

__all__ = [
    "AsyncWebCrawler",
    "CrawlResult",
    "CacheMode",
    "ExtractionStrategy",
    "ExtractionOptions",
    "CrawlTask",
    "DEFAULT_CRAWLER_CONFIG"
]
