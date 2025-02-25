import asyncio
from crawl4ai.crawler import AsyncWebCrawler
from crawl4ai.extraction_strategy import ExtractionStrategy

async def main():
    # Create crawler with selective strategy
    strategy = ExtractionStrategy("selective")
    
    async with AsyncWebCrawler() as crawler:
        # Navigate to URL and let user select elements
        result = await crawler.arun("https://example.com", strategy)
        
        if result:
            print("\nExtracted content:")
            print("-" * 50)
            print(result.content)
            print("-" * 50)
        else:
            print("No content was selected")

if __name__ == "__main__":
    asyncio.run(main())
