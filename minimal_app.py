import streamlit as st
import requests
import re
from typing import Optional

def scrape_url(url: str) -> tuple[Optional[str], Optional[str]]:
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        html_content = response.text

        # Extract text using regular expressions (a simple approach)
        text_content = re.sub(r'<[^>]+>', '', html_content)  # Remove HTML tags
        text_content = re.sub(r'\s+', ' ', text_content).strip()  # Normalize whitespace

        return text_content, None

    except requests.exceptions.RequestException as e:
        return None, f"Error fetching URL: {str(e)}"

def main():
    st.title("Web Page Scraper")
    url = st.text_input("Enter URL:", placeholder="https://example.com")

    if st.button("Scrape"):
        if url:
            with st.spinner("Scraping webpage..."):
                content, error = scrape_url(url)

                if error:
                    st.error(f"An error occurred: {error}")
                elif content:
                    st.success("Content extracted successfully!")
                    st.code(content)  # Display content
                else:
                    st.warning("No content was found on the page.")
        else:
            st.warning("Please enter a URL")

if __name__ == "__main__":
    main()
