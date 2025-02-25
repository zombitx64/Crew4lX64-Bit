import asyncio
from crawl4ai.crawl4ai.web_crawler import AsyncWebCrawler
from crawl4ai.crawl4ai.extraction_strategy import ExtractionStrategy

async def main():
    # Create crawler with LLM strategy which extracts all visible text
    strategy = ExtractionStrategy("llm")
    
    async with AsyncWebCrawler() as crawler:
        # Get the URL from user
        url = input("Enter the URL to scrape: ")
        
        # Navigate to URL and extract all content
        result = await crawler.arun(url, strategy)
        
        if result:
            print("\nExtracted content:")
            print("-" * 50)
            print(result.content)
            print("-" * 50)
        else:
            print("No content was extracted")

if __name__ == "__main__":
    asyncio.run(main())
