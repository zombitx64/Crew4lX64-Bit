from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class ExtractionStrategy(ABC):
    def __init__(self, name: str = "base"):
        self.name = name
        self._filters = []
        
    async def extract(self, driver) -> Optional[str]:
        """Extract content from the page using the strategy"""
        try:
            # Wait for content to be loaded
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                return None
                
            # Get main content based on strategy
            content = await self._extract_content(driver)
            if not content:
                return None
                
            # Apply filters
            for filter_fn in self._filters:
                content = filter_fn(content)
                if not content:
                    return None
                    
            return content.strip()
            
        except Exception as e:
            raise Exception(f"Extraction failed ({self.name}): {str(e)}")
            
    @abstractmethod
    async def _extract_content(self, driver) -> Optional[str]:
        """Strategy-specific content extraction logic"""
        pass

class RuleBasedStrategy(ExtractionStrategy):
    def __init__(self):
        super().__init__(name="rule_based")
        
    async def _extract_content(self, driver) -> Optional[str]:
        # Common content selectors
        selectors = [
            "article",
            "main",
            "[role='main']",
            ".content",
            "#content",
            ".post-content",
            ".article-content"
        ]
        
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element:
                    text = element.text
                    if text and len(text.strip()) > 100:
                        return text.strip()
            except:
                continue
                
        # Fallback to content extraction heuristics
        try:
            # Remove unwanted elements
            script = """
                const elementsToRemove = document.querySelectorAll(
                    'header, footer, nav, aside, iframe, script, style, .ads, #ads, .advertisement'
                );
                elementsToRemove.forEach(el => el.remove());
                
                // Find main content
                const article = document.querySelector('article');
                if (article) return article.textContent;
                
                // Get largest text block
                let maxLength = 0;
                let content = '';
                document.querySelectorAll('p, div').forEach(el => {
                    const text = el.textContent.trim();
                    if (text.length > maxLength) {
                        maxLength = text.length;
                        content = text;
                    }
                });
                return content;
            """
            return driver.execute_script(script)
        except:
            return None

class LLMStrategy(ExtractionStrategy):
    def __init__(self):
        super().__init__(name="llm")
        
    async def _extract_content(self, driver) -> Optional[str]:
        # Get all visible text
        script = """
            const isVisible = elem => {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0';
            };
            
            const walk = node => {
                let text = '';
                if (node.nodeType === 3) return node.data;
                if (node.nodeType === 1 && isVisible(node)) {
                    for (let child of node.childNodes) {
                        text += walk(child);
                    }
                }
                return text;
            };
            
            return walk(document.body);
        """
        text = driver.execute_script(script)
        
        if not text:
            return None
        
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text

class HybridStrategy(ExtractionStrategy):
    def __init__(self):
        super().__init__(name="hybrid")
        self.rule_based = RuleBasedStrategy()
        self.llm = LLMStrategy()
        
    async def _extract_content(self, driver) -> Optional[str]:
        # Try rule-based first
        content = await self.rule_based.extract(driver)
        
        # If rule-based fails or returns low-quality content, try LLM
        if not content or len(content.split()) < 100:
            content = await self.llm.extract(driver)
            
        return content

class SelectiveStrategy(ExtractionStrategy):
    def __init__(self):
        super().__init__(name="selective")
        self.selected_elements = []

    async def _extract_content(self, driver) -> Optional[str]:
        # Add UI elements and selection functionality
        script = """
            // Create floating controls
            const controls = document.createElement('div');
            controls.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 10000;
                background: white;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            `;
            
            // Add Select All button
            const selectAllBtn = document.createElement('button');
            selectAllBtn.textContent = 'Select All';
            selectAllBtn.style.cssText = `
                background: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                margin-right: 10px;
            `;
            controls.appendChild(selectAllBtn);
            
            // Add Reset button
            const resetBtn = document.createElement('button');
            resetBtn.textContent = 'Reset Selection';
            resetBtn.style.cssText = `
                background: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            `;
            controls.appendChild(resetBtn);
            
            document.body.appendChild(controls);
            
            // Initialize selection state
            window.selectedElements = new Set();
            window.selectAll = false;
            
            // Make elements selectable
            document.querySelectorAll('*').forEach(el => {
                if (el.textContent.trim() && !controls.contains(el)) {
                    el.style.cursor = 'pointer';
                    el.addEventListener('mouseover', (e) => {
                        if (!window.selectAll) {
                            e.stopPropagation();
                            el.style.outline = '2px solid blue';
                        }
                    });
                    el.addEventListener('mouseout', (e) => {
                        if (!window.selectAll) {
                            e.stopPropagation();
                            el.style.outline = '';
                        }
                    });
                    el.addEventListener('click', (e) => {
                        if (!window.selectAll) {
                            e.stopPropagation();
                            e.preventDefault();
                            if (window.selectedElements.has(el)) {
                                window.selectedElements.delete(el);
                                el.style.backgroundColor = '';
                            } else {
                                window.selectedElements.add(el);
                                el.style.backgroundColor = 'rgba(0, 0, 255, 0.1)';
                            }
                        }
                    });
                }
            });
            
            // Select All button functionality
            selectAllBtn.addEventListener('click', () => {
                window.selectAll = true;
                window.selectedElements.clear();
                document.querySelectorAll('*').forEach(el => {
                    if (el.textContent.trim() && !controls.contains(el)) {
                        el.style.outline = '';
                        el.style.backgroundColor = 'rgba(0, 255, 0, 0.1)';
                    }
                });
            });
            
            // Reset button functionality
            resetBtn.addEventListener('click', () => {
                window.selectAll = false;
                window.selectedElements.clear();
                document.querySelectorAll('*').forEach(el => {
                    if (el.textContent.trim() && !controls.contains(el)) {
                        el.style.backgroundColor = '';
                    }
                });
            });
        """
        driver.execute_script(script)
        
        # Wait for user selection
        input("Select elements to scrape (or click 'Select All'), then press Enter to continue...")
        
        # Get content based on selection
        extract_script = """
            if (window.selectAll) {
                // Get all visible text if Select All was clicked
                return Array.from(document.querySelectorAll('*'))
                    .filter(el => el.textContent.trim() && !el.closest('[style*="position: fixed"]'))
                    .map(el => el.textContent.trim())
                    .join('\\n\\n');
            } else {
                // Get only selected elements' text
                return Array.from(window.selectedElements)
                    .map(el => el.textContent.trim())
                    .join('\\n\\n');
            }
        """
        content = driver.execute_script(extract_script)
        
        if not content:
            return None
            
        return content.strip()

def ExtractionStrategy(strategy_name: str = "rule_based") -> ExtractionStrategy:
    """Factory function to create extraction strategy instances"""
    strategies = {
        "rule_based": RuleBasedStrategy,
        "llm": LLMStrategy,
        "hybrid": HybridStrategy,
        "selective": SelectiveStrategy
    }
    
    strategy_class = strategies.get(strategy_name.lower())
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}")
        
    return strategy_class()
