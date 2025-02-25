# Minimal Streamlit Web Scraper App

This is a simple web scraping application built with Streamlit and Python. It allows users to enter a URL and extract the text content from the webpage.

## Requirements

- Python 3.7+
- Streamlit
- Requests

## Installation

1.  Install the required libraries:

    ```bash
    pip install streamlit requests
    ```

## Usage

1.  Run the application:

    ```bash
    streamlit run minimal_app.py
    ```

2.  Open the provided URL in your web browser (usually `http://localhost:8501`).

3.  Enter the URL of the webpage you want to scrape in the text input field.

4.  Click the "Scrape" button.

5.  The extracted text content will be displayed below the button.

## Notes

- This is a basic scraper and may not work correctly on all websites.
- It uses regular expressions to remove HTML tags, which is a simple approach and may not be perfect for all cases.
- Error handling is included to catch issues with fetching the URL.
