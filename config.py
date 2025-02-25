MIN_WORD_THRESHOLD = 50
MODEL_REPO_BRANCH = "main"  # Default branch for model repository

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
    "timeout": 20,  # seconds
    "wait_until": "networkidle",
    "javascript": True,
    "max_retries": 2,
    
    # Navigation settings
    "max_depth": 3,  # Default depth increased to match common use cases
    "follow_links": False,
    
    # Cache settings
    "cache_mode": "memory",  # Options: "memory", "disk", "none"
    "cache_expiry": 3600,  # seconds (1 hour)
    
    # Content extraction
    "min_content_length": 100,  # Minimum length of content in characters
    "extract_metadata": True,
    "ignore_robots": False,
    
    # Performance
    "concurrent_requests": 2,
    "request_delay": 1.0  # seconds
}

class CrawlerConfig:
    """
    Configuration class for web crawler settings.
    
    This class manages crawler configuration with default values, validation,
    and flexible updates from dictionaries or keyword arguments.
    
    Attributes:
        max_depth (int): Maximum depth for crawling (default: 3)
        timeout (int): Page load timeout in seconds (default: 30)
        cache_mode (str): Cache storage mode ("memory", "disk", or "none", default: "memory")
        browser_args (list): Browser launch arguments (default from DEFAULT_CRAWLER_CONFIG)
        wait_until (str): Page load condition ("load", "domcontentloaded", "networkidle", default: "networkidle")
        javascript (bool): Enable JavaScript execution (default: True)
        max_retries (int): Maximum retry attempts for failed requests (default: 2)
        follow_links (bool): Whether to follow links during crawling (default: False)
        cache_expiry (int): Cache expiration time in seconds (default: 3600)
        min_content_length (int): Minimum content length for valid pages (default: 100)
        extract_metadata (bool): Whether to extract page metadata (default: True)
        ignore_robots (bool): Whether to ignore robots.txt (default: False)
        concurrent_requests (int): Number of concurrent requests (default: 2)
        request_delay (float): Delay between requests in seconds (default: 1.0)
    """
    
    VALID_CACHE_MODES = {"memory", "disk", "none"}
    VALID_WAIT_UNTIL = {"load", "domcontentloaded", "networkidle"}

    def __init__(self, **kwargs):
        """
        Initialize CrawlerConfig with default values from DEFAULT_CRAWLER_CONFIG.
        
        Args:
            **kwargs: Optional parameters to override default values
        """
        # Set default values from DEFAULT_CRAWLER_CONFIG
        for key, value in DEFAULT_CRAWLER_CONFIG.items():
            setattr(self, key, value)
        
        # Update with any provided kwargs, with validation
        self.update(**kwargs)
    
    def update(self, **kwargs):
        """
        Update configuration values with validation.
        
        Args:
            **kwargs: Key-value pairs to update configuration
            
        Raises:
            ValueError: If a value is invalid for a given parameter
            TypeError: If a parameter type is incorrect
        """
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise ValueError(f"Unknown configuration parameter: {key}")
            
            if key == "cache_mode":
                if value not in self.VALID_CACHE_MODES:
                    raise ValueError(f"Invalid cache mode. Must be one of {self.VALID_CACHE_MODES}")
            elif key == "wait_until":
                if value not in self.VALID_WAIT_UNTIL:
                    raise ValueError(f"Invalid wait_until value. Must be one of {self.VALID_WAIT_UNTIL}")
            elif key == "max_depth":
                if not isinstance(value, int) or value < 0:
                    raise ValueError("max_depth must be a non-negative integer")
            elif key == "timeout":
                if not isinstance(value, (int, float)) or value <= 0:
                    raise ValueError("timeout must be a positive number")
            elif key == "max_retries":
                if not isinstance(value, int) or value < 0:
                    raise ValueError("max_retries must be a non-negative integer")
            elif key == "follow_links":
                if not isinstance(value, bool):
                    raise ValueError("follow_links must be a boolean")
            elif key == "cache_expiry":
                if not isinstance(value, (int, float)) or value <= 0:
                    raise ValueError("cache_expiry must be a positive number")
            elif key == "min_content_length":
                if not isinstance(value, int) or value < 0:
                    raise ValueError("min_content_length must be a non-negative integer")
            elif key == "extract_metadata":
                if not isinstance(value, bool):
                    raise ValueError("extract_metadata must be a boolean")
            elif key == "ignore_robots":
                if not isinstance(value, bool):
                    raise ValueError("ignore_robots must be a boolean")
            elif key == "concurrent_requests":
                if not isinstance(value, int) or value <= 0:
                    raise ValueError("concurrent_requests must be a positive integer")
            elif key == "request_delay":
                if not isinstance(value, (int, float)) or value < 0:
                    raise ValueError("request_delay must be a non-negative number")
            elif key == "browser_args":
                if not isinstance(value, (list, tuple)):
                    raise ValueError("browser_args must be a list or tuple of strings")
                if not all(isinstance(arg, str) for arg in value):
                    raise ValueError("browser_args must contain only strings")
            elif key == "javascript":
                if not isinstance(value, bool):
                    raise ValueError("javascript must be a boolean")

            setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, config_dict):
        """
        Create a CrawlerConfig instance from a dictionary.
        
        Args:
            config_dict (dict): Dictionary containing configuration parameters
            
        Returns:
            CrawlerConfig: New instance with values from the dictionary
        """
        instance = cls()
        instance.update(**config_dict)
        return instance
    
    def to_dict(self):
        """
        Convert configuration to a dictionary.
        
        Returns:
            dict: Dictionary representation of the configuration
        """
        return {key: getattr(self, key) for key in DEFAULT_CRAWLER_CONFIG.keys()}
    
    def validate(self):
        """
        Validate the current configuration.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        self.update(**self.to_dict())  # This will trigger validation

# Example usage
if __name__ == "__main__":
    # Create a default config
    config = CrawlerConfig()
    print("Default config:", config.to_dict())
    
    # Update with custom values
    config.update(max_depth=5, timeout=60, follow_links=True, cache_mode="disk")
    print("Updated config:", config.to_dict())
    
    # Create from dictionary
    custom_config = {
        "max_depth": 4,
        "timeout": 45,
        "javascript": False,
        "concurrent_requests": 4
    }
    new_config = CrawlerConfig.from_dict(custom_config)
    print("Config from dict:", new_config.to_dict())
    
    try:
        # Test invalid value
        config.update(cache_mode="invalid")
    except ValueError as e:
        print("Validation error:", str(e))