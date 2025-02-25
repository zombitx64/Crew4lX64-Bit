"""
SQLite database module for crawled data management.

This module provides a complete interface for managing crawled webpage data in a SQLite database.
It handles connection management, error handling, data caching, searching, and exports.

Key Features:
- Connection pooling and retry logic via database_connection decorator
- Progress tracking via LoadingState observer pattern
- Efficient pagination and search functionality
- Multiple export formats (JSON, CSV, Markdown)
- JSON field serialization/deserialization
- Transaction management
- Error handling and logging

Example Usage:
    # Initialize database
    init_db()
    
    # Cache crawled data
    data = {'url': 'https://example.com', 'html': '<html>...</html>', ...}
    cache_url('https://example.com', data)
    
    # Search for content
    results, total = search_records('example', page=1, per_page=10)
"""

import os
from pathlib import Path
import sqlite3
import json
from typing import Optional, Tuple, List, Dict
import datetime
import shutil
import logging
import io
import csv
from contextlib import contextmanager
from time import sleep

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def database_connection(func):
    """
    Decorator to handle SQLite database connections.
    
    Provides connection management, error handling, and retry logic for database operations.
    The decorated function receives a cursor object as its first argument.
    
    Handles:
    - Connection creation and cleanup
    - Transaction management (commit/rollback)
    - Error handling with retries (up to MAX_CONNECTION_ATTEMPTS)
    - Connection timeouts (CONNECTION_TIMEOUT seconds)
    
    Example:
        @database_connection
        def my_db_function(cursor: sqlite3.Cursor, *args, **kwargs):
            cursor.execute("SELECT * FROM my_table")
            return cursor.fetchall()
    """
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_CONNECTION_ATTEMPTS):
            try:
                with sqlite3.connect(DB_PATH, timeout=CONNECTION_TIMEOUT) as conn:
                    cursor = conn.cursor()
                    result = func(cursor, *args, **kwargs)
                    return result
            except sqlite3.Error as e:
                logger.error(f"Database operation failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_CONNECTION_ATTEMPTS - 1:
                    sleep(RETRY_DELAY)
                else:
                    raise RuntimeError(f"Database operation failed after {MAX_CONNECTION_ATTEMPTS} attempts") from e
    return wrapper

class LoadingState:
    """
    Singleton class to manage loading state and notify observers.
    
    This class implements the Observer pattern to notify registered callbacks
    about changes in loading state. It's used to track and communicate the
    progress of database operations.
    
    Attributes:
        _instance: Singleton instance of the class
        _callbacks: List of callback functions to be notified of state changes
    """
    _instance = None
    _callbacks = []

    def __new__(cls):
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_callback(cls, callback):
        """
        Register a callback function to be notified of loading state changes.
        
        Args:
            callback: Function that takes two parameters:
                - is_loading (bool): Whether an operation is in progress
                - message (str): Description of the current operation
        """
        cls._callbacks.append(callback)

    @classmethod
    def notify_listeners(cls, is_loading: bool, message: str = ""):
        """
        Notify all registered callbacks about a loading state change.
        
        Args:
            is_loading (bool): Whether an operation is starting (True) or ending (False)
            message (str): Description of the current operation
        """
        for callback in cls._callbacks:
            callback(is_loading, message)

@contextmanager
def loading_operation(message: str = "Loading..."):
    """
    Context manager for tracking database operation progress.
    
    Notifies registered LoadingState callbacks when an operation starts and ends.
    Ensures notifications are sent even if the operation raises an exception.
    
    Args:
        message (str): Description of the operation being performed
        
    Example:
        with loading_operation("Processing data..."):
            # Do some work
            process_data()
        # Loading state is automatically cleared after the block
    """
    try:
        LoadingState.notify_listeners(True, message)
        yield
    finally:
        LoadingState.notify_listeners(False, "")

# Database configuration
DB_PATH = os.path.join(os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home()), ".crawl4ai", "crawl4ai.db")
MAX_CONNECTION_ATTEMPTS = 3
CONNECTION_TIMEOUT = 10  # seconds
RETRY_DELAY = 1  # second
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

@database_connection
def init_db(cursor: sqlite3.Cursor) -> None:
    """
    Initialize the SQLite database with the crawled_data table.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        
    Returns:
        None
    """
    with loading_operation("Initializing database..."):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crawled_data (
                url TEXT PRIMARY KEY,
                html TEXT,
                cleaned_html TEXT,
                markdown TEXT,
                extracted_content TEXT,
                success INTEGER DEFAULT 1,
                media TEXT DEFAULT "{}",
                links TEXT DEFAULT "{}",
                metadata TEXT DEFAULT "{}",
                screenshot TEXT DEFAULT "",
                timestamp REAL DEFAULT (strftime('%s', 'now'))
            )
        """)
        logger.info("Database initialized successfully.")

@database_connection
def get_total_count(cursor: sqlite3.Cursor) -> int:
    """
    Get the total number of records in the database.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        
    Returns:
        int: Total number of records in the database
    """
    with loading_operation("Counting records..."):
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        return cursor.fetchone()[0]

@database_connection
def get_crawl_statistics(cursor: sqlite3.Cursor) -> dict:
    """
    Get comprehensive crawl statistics from the database.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        
    Returns:
        dict: Dictionary containing statistics:
            - total_urls: Total number of URLs in database
            - successful_crawls: Number of successful crawls
            - failed_crawls: Number of failed crawls
            - avg_content_length: Average length of extracted content
            - avg_media_per_url: Average number of media items per URL
            - avg_links_per_url: Average number of links per URL
            - first_crawl: ISO formatted timestamp of first crawl
            - last_crawl: ISO formatted timestamp of last crawl
    """
    with loading_operation("Calculating statistics..."):
        stats = {}
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        stats['total_urls'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM crawled_data WHERE success = 1")
        stats['successful_crawls'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM crawled_data WHERE success = 0")
        stats['failed_crawls'] = cursor.fetchone()[0]
        
        # Content analysis
        cursor.execute("SELECT AVG(LENGTH(extracted_content)) FROM crawled_data")
        stats['avg_content_length'] = round(cursor.fetchone()[0] or 0, 2)
        
        # Media/Link analysis
        cursor.execute("SELECT AVG(JSON_ARRAY_LENGTH(media)) FROM crawled_data")
        stats['avg_media_per_url'] = round(cursor.fetchone()[0] or 0, 2)
        
        cursor.execute("SELECT AVG(JSON_ARRAY_LENGTH(links)) FROM crawled_data")
        stats['avg_links_per_url'] = round(cursor.fetchone()[0] or 0, 2)
        
        # Timeline stats
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM crawled_data")
        min_ts, max_ts = cursor.fetchone()
        stats['first_crawl'] = datetime.datetime.fromtimestamp(min_ts).isoformat() if min_ts else None
        stats['last_crawl'] = datetime.datetime.fromtimestamp(max_ts).isoformat() if max_ts else None
        
        return stats

@database_connection
def get_cached_url(cursor: sqlite3.Cursor, url: str) -> Optional[Dict]:
    """
    Get cached data for a URL if it exists.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        url (str): The URL to look up in the cache
        
    Returns:
        Optional[Dict]: Dictionary containing cached data if found, None otherwise
            Keys include: url, html, cleaned_html, markdown, extracted_content,
            success, media (JSON), links (JSON), metadata (JSON), screenshot,
            timestamp (datetime)
    """
    with loading_operation(f"Retrieving cached data for {url}..."):
        cursor.execute(
            "SELECT * FROM crawled_data WHERE url = ?", (url,)
        )
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            result['links'] = json.loads(result.get('links', '{}'))
            result['media'] = json.loads(result.get('media', '{}'))
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['timestamp'] = datetime.datetime.fromtimestamp(result['timestamp'])
            return result
        return None

@database_connection
def cache_url(cursor: sqlite3.Cursor, url: str, data: Dict) -> bool:
    """
    Cache crawled data for a URL.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        url (str): The URL to cache
        data (Dict): The data to cache, should contain:
            - html: Raw HTML content
            - cleaned_html: Cleaned HTML content
            - markdown: Markdown version of content
            - extracted_content: Plain text content
            - success: Boolean indicating crawl success
            - media: Dictionary of media items
            - links: Dictionary of internal/external links
            - metadata: Dictionary of metadata
            - screenshot: Optional screenshot data
            
    Returns:
        bool: True if caching was successful
    """
    with loading_operation(f"Caching data for {url}..."):
        # Ensure all required fields are present
        required_fields = ['html', 'cleaned_html', 'markdown', 'extracted_content', 'success']
        for field in required_fields:
            if field not in data:
                data[field] = '' if field != 'success' else 1

        # Convert dictionary data to JSON strings where needed
        data['links'] = json.dumps(data.get('links', {}))
        data['media'] = json.dumps(data.get('media', {}))
        data['metadata'] = json.dumps(data.get('metadata', {}))

        # Insert or replace record
        cursor.execute(
            """
            INSERT OR REPLACE INTO crawled_data 
            (url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            """,
            (
                url,
                data.get('html', ''),
                data.get('cleaned_html', ''),
                data.get('markdown', ''),
                data.get('extracted_content', ''),
                data.get('success', 1),
                data['media'],
                data['links'],
                data['metadata'],
                data.get('screenshot', '')
            )
        )
        logger.info(f"Successfully cached URL: {url}")
        return True

@database_connection
def get_records_paginated(cursor: sqlite3.Cursor, page: int = 1, per_page: int = 10) -> Tuple[List[Dict], int]:
    """
    Get paginated records from the database.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        page (int): Page number, starting from 1
        per_page (int): Number of records per page
        
    Returns:
        Tuple[List[Dict], int]: Tuple containing:
            - List of record dictionaries with parsed JSON fields and converted timestamps
            - Total number of records in database
    """
    with loading_operation(f"Loading page {page}..."):
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        total = cursor.fetchone()[0]
        
        # Get paginated records with efficient indexing
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT * FROM crawled_data 
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
            """, 
            (per_page, offset)
        )
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            result['links'] = json.loads(result.get('links', '{}'))
            result['media'] = json.loads(result.get('media', '{}'))
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['timestamp'] = datetime.datetime.fromtimestamp(result['timestamp'])
            results.append(result)
        
        return results, total

@database_connection
def export_data(cursor: sqlite3.Cursor, format: str = 'json') -> List[str]:
    """
    Generate export data in specified format.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        format (str): Export format - one of: 'json', 'csv', 'md'
        
    Returns:
        List[str]: Chunks of formatted data, where:
            - JSON: Each chunk is a list of records as JSON string
            - CSV: Single chunk containing all records in CSV format
            - Markdown: Chunks of markdown text (~1MB each)
            
    Raises:
        ValueError: If format is not one of the supported types
    """
    with loading_operation(f"Exporting data as {format}..."):
        # Query all data at once
        cursor.execute(
            "SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot, timestamp FROM crawled_data"
        )
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        # Convert rows to dict list for easier processing
        results = []
        for row in rows:
            result = dict(zip(columns, row))
            result['links'] = json.loads(result.get('links', '{}'))
            result['media'] = json.loads(result.get('media', '{}'))
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['timestamp'] = datetime.datetime.fromtimestamp(result['timestamp'])
            results.append(result)

        # Format the data based on requested format
        formatted_chunks = []
        
        if format.lower() == 'json':
            # Process in chunks for large datasets
            chunk_size = 100
            for i in range(0, len(results), chunk_size):
                chunk = results[i:i + chunk_size]
                formatted_chunks.append(json.dumps(chunk, indent=2, ensure_ascii=False) + "\n")
                
        elif format.lower() == 'csv':
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            for result in results:
                writer.writerow(result)
            formatted_chunks.append(output.getvalue())
            
        elif format.lower() == 'md':
            # Process each result into markdown
            current_chunk = []
            for result in results:
                md_parts = []
                md_parts.append(f"# {result['url']}\n\n")
                
                if result.get('markdown'):
                    md_parts.append(f"{result['markdown']}\n\n")
                
                links = result.get('links', {})
                if links:
                    md_parts.append("## Links\n\n")
                    if links.get('internal'):
                        md_parts.append("### Internal Links\n\n")
                        for link in links['internal']:
                            md_parts.append(f"- [{link.get('text', link.get('href', 'Link'))}]({link.get('href', '')})\n")
                        md_parts.append("\n")
                    if links.get('external'):
                        md_parts.append("### External Links\n\n")
                        for link in links['external']:
                            md_parts.append(f"- [{link.get('text', link.get('href', 'Link'))}]({link.get('href', '')})\n")
                        md_parts.append("\n")
                
                md_parts.append("---\n\n")
                current_chunk.append("".join(md_parts))
                
                # Add chunk to formatted_chunks when it gets large enough
                if len("".join(current_chunk).encode('utf-8')) > 1024 * 1024:  # 1MB chunks
                    formatted_chunks.append("".join(current_chunk))
                    current_chunk = []
            
            # Add any remaining content
            if current_chunk:
                formatted_chunks.append("".join(current_chunk))
        logger.info(f"Exported {len(results)} records in {format} format")
        return formatted_chunks

@database_connection
def search_records(cursor: sqlite3.Cursor, query: str, page: int = 1, per_page: int = 10) -> Tuple[List[Dict], int]:
    """
    Search records in the database with pagination.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        query (str): Search query to match against URLs and content
        page (int): Page number, starting from 1
        per_page (int): Number of records per page
        
    Returns:
        Tuple[List[Dict], int]: Tuple containing:
            - List of matching record dictionaries with parsed JSON fields
            - Total number of matching records
    """
    with loading_operation(f"Searching for '{query}' on page {page}..."):
        # Get total count of matching records
        cursor.execute(
            """
            SELECT COUNT(*) FROM crawled_data 
            WHERE url LIKE ? OR extracted_content LIKE ?
            """,
            (f"%{query}%", f"%{query}%")
        )
        total = cursor.fetchone()[0]

        # Get paginated results
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT * FROM crawled_data 
            WHERE url LIKE ? OR extracted_content LIKE ?
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
            """,
            (f"%{query}%", f"%{query}%", per_page, offset)
        )
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            result['links'] = json.loads(result.get('links', '{}'))
            result['media'] = json.loads(result.get('media', '{}'))
            result['metadata'] = json.loads(result.get('metadata', '{}'))
            result['timestamp'] = datetime.datetime.fromtimestamp(result['timestamp'])
            results.append(result)
        
        return results, total

@database_connection
def delete_record(cursor: sqlite3.Cursor, url: str) -> bool:
    """
    Delete a record from the database.
    
    Args:
        cursor (sqlite3.Cursor): Database cursor provided by the connection decorator
        url (str): URL of the record to delete
        
    Returns:
        bool: True if a record was deleted, False if no matching record was found
    """
    with loading_operation(f"Deleting record for {url}..."):
        cursor.execute("DELETE FROM crawled_data WHERE url = ?", (url,))
        affected_rows = cursor.rowcount
        logger.info(f"Successfully deleted record for URL: {url}, Rows affected: {affected_rows}")
        return affected_rows > 0