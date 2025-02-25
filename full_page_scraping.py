import asyncio
from playwright.async_api import Page
from playwright.async_api import async_playwright
import re

class LLMStrategy:
    async def extract(self, page: Page) -> str:
        # Get all visible text using JavaScript
        script = """(() => {
            const isVisible = elem => {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0';
            };
            
            const walk = node => {
                let text = '';
                if (node.nodeType === 3) {
                    text += node.data + ' ';
                } else if (node.nodeType === 1 && isVisible(node)) {
                    for (let child of node.childNodes) {
                        text += walk(child);
                    }
                    // Add line breaks for block elements
                    if (getComputedStyle(node).display === 'block') {
                        text += '\\n';
                    }
                }
                return text;
            };
            
            return walk(document.body);
        })()
        """
        text = await page.evaluate(script)
        
        if not text:
            return None
        
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text

async def main():
    url = input("Enter the URL to scrape: ")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials'
            ]
        )
        page = await browser.new_page()
        
        try:
            # Increase timeout and wait until network is idle
            await page.goto(url, timeout=60000, wait_until='networkidle')
            # Wait additional time for dynamic content
            await page.wait_for_timeout(2000)
            strategy = LLMStrategy()
            content = await strategy.extract(page)
            
            if content:
                print("\nExtracted content:")
                print("-" * 50)
                print(content)
                print("-" * 50)
            else:
                print("No content was extracted")
                
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
