import streamlit as st
from playwright.sync_api import sync_playwright
import re
from typing import Optional

class LLMStrategy:
    def extract(self, page) -> Optional[str]:
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
        })()"""
        
        text = page.evaluate(script)
        
        if not text:
            return None
        
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text

def scrape_url(url: str) -> tuple[Optional[str], Optional[str]]:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            page = browser.new_page()
            
            try:
                page.goto(url, timeout=60000, wait_until='networkidle')
                page.wait_for_timeout(2000)
                
                strategy = LLMStrategy()
                content = strategy.extract(page)
                
                if content:
                    return content, None
                else:
                    return None, "No content was extracted"
                    
            except Exception as e:
                return None, f"Error accessing page: {str(e)}"
            finally:
                browser.close()
    except Exception as e:
        return None, f"Browser error: {str(e)}"

def main():
    st.set_page_config(
        page_title="Web Page Scraper",
        page_icon="🌐",
        layout="wide"
    )
    
    st.title("Web Page Scraper 🌐")
    st.write("Enter a URL below to extract all visible text from the webpage, or try one of the examples.")

    # Example URLs
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Example 1 (OriginsHQ)"):
            url = "https://originshq.com/blog/top-ai-llm-learning-resource-in-2025/"
    with col2:
        if st.button("Example 2 (Wikipedia)"):
            url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    with col3:
        if st.button("Example 3 (Hacker News)"):
            url = "https://news.ycombinator.com/"

    url = st.text_input("Enter URL:", placeholder="https://example.com", value=url if 'url' in locals() else '')

    if st.button("Scrape"):
        if url:
            with st.spinner("Scraping webpage..."):
                content, error = scrape_url(url)

                if error:
                    st.error(f"An error occurred: {error}")
                elif content:
                    st.success("Content extracted successfully!")

                    # Add download button
                    st.download_button(
                        label="Download as Text File",
                        data=content,
                        file_name="scraped_content.txt",
                        mime="text/plain"
                    )

                    # Display content in expandable section
                    with st.expander("View Extracted Content", expanded=True):
                        st.code(content, language="plaintext")
                else:
                    st.warning("No content was found on the page.")
        else:
            st.warning("Please enter a URL")

    st.write("This is a test to see if Streamlit is working.")
import streamlit as st
from playwright.sync_api import sync_playwright
import re
from typing import Optional

class LLMStrategy:
    def extract(self, page) -> Optional[str]:
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
        })()"""
        
        text = page.evaluate(script)
        
        if not text:
            return None
        
        # Clean and normalize text
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text

def scrape_url(url: str) -> tuple[Optional[str], Optional[str]]:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            page = browser.new_page()
            
            try:
                page.goto(url, timeout=60000, wait_until='networkidle')
                page.wait_for_timeout(2000)
                
                strategy = LLMStrategy()
                content = strategy.extract(page)
                
                if content:
                    return content, None
                else:
                    return None, "No content was extracted"
                    
            except Exception as e:
                return None, f"Error accessing page: {str(e)}"
            finally:
                browser.close()
    except Exception as e:
        return None, f"Browser error: {str(e)}"

def main():
    st.set_page_config(
        page_title="Web Page Scraper",
        page_icon="🌐",
        layout="wide"
    )
    
    st.title("Web Page Scraper 🌐")
    st.write("Enter a URL below to extract all visible text from the webpage, or try one of the examples.")

    # Example URLs
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Example 1 (OriginsHQ)"):
            url = "https://originshq.com/blog/top-ai-llm-learning-resource-in-2025/"
    with col2:
        if st.button("Example 2 (Wikipedia)"):
            url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    with col3:
        if st.button("Example 3 (Hacker News)"):
            url = "https://news.ycombinator.com/"

    url = st.text_input("Enter URL:", placeholder="https://example.com", value=url if 'url' in locals() else '')

    if st.button("Scrape"):
        if url:
            with st.spinner("Scraping webpage..."):
                content, error = scrape_url(url)

                if error:
                    st.error(f"An error occurred: {error}")
                elif content:
                    st.success("Content extracted successfully!")

                    # Add download button
                    st.download_button(
                        label="Download as Text File",
                        data=content,
                        file_name="scraped_content.txt",
                        mime="text/plain"
                    )

                    # Display content in expandable section
                    with st.expander("View Extracted Content", expanded=True):
                        st.text_area("Content", content, height=500, key="content_area", disabled=True)
                else:
                    st.warning("No content was found on the page.")
        else:
            st.warning("Please enter a URL")


    st.markdown("""
    <style>
    .stTextArea [data-baseweb="textarea"] {
        font-family: monospace;
    }
    </style>
    """, unsafe_allow_html=True)
