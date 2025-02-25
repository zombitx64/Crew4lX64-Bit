MIN_WORD_THRESHOLD = 50

# Default crawler configuration
DEFAULT_CRAWLER_CONFIG = {
    # Browser settings
    "browser_args": [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-accelerated-2d-canvas",
        "--disable-gpu",
        "--disable-infobars"
    ],
    
    # Page load settings
    "timeout": 20,
    "wait_until": "networkidle",
    "javascript": True,
    "max_retries": 2,
    
    # Navigation settings
    "max_depth": 1,
    "follow_links": False,
    
    # Cache settings
    "cache_mode": "memory",
    "cache_expiry": 3600,
    
    # Content extraction
    "min_content_length": 100,
    "extract_metadata": True,
    "ignore_robots": False,
    
    # Performance
    "concurrent_requests": 2,
    "request_delay": 1.0
}

class CrawlerConfig:
    def __init__(self, max_depth=3, timeout=30, cache_mode="memory"):
        self.max_depth = max_depth
        self.timeout = timeout
        self.cache_mode = cache_mode
        
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    @classmethod
    def from_dict(cls, config_dict):
        instance = cls()
        instance.update(**config_dict)
        return instance
