import asyncio
from typing import Optional, List, Dict, Any
from .config import DEFAULT_CRAWLER_CONFIG, CrawlerConfig
from .extraction_strategy import ExtractionStrategy
from .models import CrawlResult

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

class AsyncWebCrawler:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CRAWLER_CONFIG}
        if config:
            self.config.update(config)
        
        self._driver = None
        self._initialized = False

    async def __aenter__(self):
        try:
            # Set up Chrome options
            chrome_options = Options()
            for arg in self.config["browser_args"]:
                chrome_options.add_argument(arg)
            chrome_options.add_argument("--headless")
            
            # Initialize Chrome driver
            self._driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            
            # Set timeouts
            self._driver.set_page_load_timeout(self.config["timeout"])
            self._driver.implicitly_wait(5)
            
            self._initialized = True
            return self
            
        except Exception as e:
            await self.cleanup()
            raise Exception(f"Failed to initialize crawler: {str(e)}")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def cleanup(self):
        if self._driver:
            self._driver.quit()
        self._initialized = False

    async def arun(self, url: str, strategy: ExtractionStrategy, word_count_threshold: int = 50) -> Optional[CrawlResult]:
        if not self._initialized:
            raise Exception("Crawler not initialized. Use 'async with' context manager.")

        try:
            # Convert HttpUrl to string and navigate to URL
            url_str = str(url)
            for attempt in range(self.config["max_retries"]):
                try:
                    self._driver.get(url_str)
                    # Wait for body to be present
                    WebDriverWait(self._driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    break
                except TimeoutException:
                    if attempt == self.config["max_retries"] - 1:
                        raise Exception("Page load timed out")
                    await asyncio.sleep(1)
            
            # Get page title
            title = self._driver.title
            
            # Extract content using strategy
            content = await strategy.extract(self._driver)
            
            if not content:
                return None
            
            # Create result
            result = CrawlResult(
                url=url_str,
                title=title,
                content=content,
                metadata={
                    "strategy": strategy.name,
                    "word_count": len(content.split()),
                    "timestamp": self._driver.execute_script("return new Date().toISOString();")
                }
            )
            
            return result
            
        except Exception as e:
            raise Exception(f"Error during crawling: {str(e)}")
