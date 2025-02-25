import os
from pathlib import Path
import sqlite3
import json
from typing import Optional, Tuple, List, Dict
import datetime
import shutil

DB_PATH = os.path.join(os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home()), ".crawl4ai")
os.makedirs(DB_PATH, exist_ok=True)
DB_PATH = os.path.join(DB_PATH, "crawl4ai.db")


def init_db():
    global DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS crawled_data (
            url TEXT PRIMARY KEY,
            html TEXT,
            cleaned_html TEXT,
            markdown TEXT,
            extracted_content TEXT,
            success BOOLEAN,
            media TEXT DEFAULT "{}",
            links TEXT DEFAULT "{}",
            metadata TEXT DEFAULT "{}",
            screenshot TEXT DEFAULT ""
        )
    """
    )
    conn.commit()
    conn.close()


def alter_db_add_screenshot(new_column: str = "media"):
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f'ALTER TABLE crawled_data ADD COLUMN {new_column} TEXT DEFAULT ""'
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error altering database to add screenshot column: {e}")


def check_db_path():
    if not DB_PATH:
        raise ValueError("Database path is not set or is empty.")


def get_cached_url(
    url: str,
) -> Optional[Tuple[str, str, str, str, str, str, str, bool, str]]:
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot FROM crawled_data WHERE url = ?",
            (url,),
        )
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        print(f"Error retrieving cached URL: {e}")
        return None


def cache_url(
    url: str,
    html: str,
    cleaned_html: str,
    markdown: str,
    extracted_content: str,
    success: bool,
    media: str = "{}",
    links: str = "{}",
    metadata: str = "{}",
    screenshot: str = "",
):
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO crawled_data (url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                html = excluded.html,
                cleaned_html = excluded.cleaned_html,
                markdown = excluded.markdown,
                extracted_content = excluded.extracted_content,
                success = excluded.success,
                media = excluded.media,      
                links = excluded.links,    
                metadata = excluded.metadata,      
                screenshot = excluded.screenshot
        """,
            (
                url,
                html,
                cleaned_html,
                markdown,
                extracted_content,
                success,
                media,
                links,
                metadata,
                screenshot,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error caching URL: {e}")


def get_total_count() -> int:
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        result = cursor.fetchone()
        conn.close()
        return result[0]
    except Exception as e:
        print(f"Error getting total count: {e}")
        return 0


def clear_db():
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crawled_data")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error clearing database: {e}")


def flush_db():
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE crawled_data")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error flushing database: {e}")


def update_existing_records(new_column: str = "media", default_value: str = "{}"):
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f'UPDATE crawled_data SET {new_column} = "{default_value}" WHERE screenshot IS NULL'
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating existing records: {e}")


def search_by_url_pattern(pattern: str, limit: int = 100) -> List[Dict]:
    """Search for URLs matching a pattern and return their data"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot 
            FROM crawled_data 
            WHERE url LIKE ? 
            LIMIT ?
            """,
            (f"%{pattern}%", limit)
        )
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        conn.close()
        return results
    except Exception as e:
        print(f"Error searching URLs: {e}")
        return []

def get_records_paginated(page: int = 1, per_page: int = 10) -> Tuple[List[Dict], int]:
    """Get paginated records with total count"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        total = cursor.fetchone()[0]
        
        # Get paginated results
        offset = (page - 1) * per_page
        cursor.execute(
            """
            SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot 
            FROM crawled_data 
            LIMIT ? OFFSET ?
            """,
            (per_page, offset)
        )
        
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
            
        conn.close()
        return results, total
    except Exception as e:
        print(f"Error getting paginated records: {e}")
        return [], 0

def export_data(output_file: str, format: str = 'json'):
    """Export database data to JSON, CSV, or Markdown format"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot FROM crawled_data"
        )
        
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        if format.lower() == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        elif format.lower() == 'csv':
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows(results)
        elif format.lower() == 'md':
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in results:
                    # Write URL as header
                    f.write(f"# {result['url']}\n\n")
                    
                    # Write markdown content if available
                    if result.get('markdown'):
                        f.write(f"{result['markdown']}\n\n")
                    
                    # Write links section if available
                    links = json.loads(result.get('links', '{}'))
                    if links:
                        f.write("## Links\n\n")
                        if links.get('internal'):
                            f.write("### Internal Links\n\n")
                            for link in links['internal']:
                                f.write(f"- [{link.get('text', link.get('href', 'Link'))}]({link.get('href', '')})\n")
                            f.write("\n")
                        if links.get('external'):
                            f.write("### External Links\n\n")
                            for link in links['external']:
                                f.write(f"- [{link.get('text', link.get('href', 'Link'))}]({link.get('href', '')})\n")
                            f.write("\n")
                    
                    # Add separator between pages
                    f.write("---\n\n")
                
        conn.close()
    except Exception as e:
        print(f"Error exporting data: {e}")

def get_crawl_statistics() -> Dict:
    """Get statistics about crawled data"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM crawled_data")
        stats['total_records'] = cursor.fetchone()[0]
        
        # Successful crawls
        cursor.execute("SELECT COUNT(*) FROM crawled_data WHERE success = 1")
        stats['successful_crawls'] = cursor.fetchone()[0]
        
        # Failed crawls
        cursor.execute("SELECT COUNT(*) FROM crawled_data WHERE success = 0")
        stats['failed_crawls'] = cursor.fetchone()[0]
        
        # Records with screenshots
        cursor.execute("SELECT COUNT(*) FROM crawled_data WHERE screenshot != ''")
        stats['records_with_screenshots'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return {}

def backup_database(backup_path: Optional[str] = None) -> str:
    """Create a backup of the database"""
    check_db_path()
    if backup_path is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{DB_PATH}_backup_{timestamp}"
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        return backup_path
    except Exception as e:
        print(f"Error creating backup: {e}")
        return ""

def restore_database(backup_path: str) -> bool:
    """Restore database from a backup"""
    check_db_path()
    if not os.path.exists(backup_path):
        print(f"Backup file not found: {backup_path}")
        return False
        
    try:
        shutil.copy2(backup_path, DB_PATH)
        return True
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return False

def search_content(query: str, limit: int = 100) -> List[Dict]:
    """Search through extracted content and return matching records"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot
            FROM crawled_data 
            WHERE extracted_content LIKE ? 
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        conn.close()
        return results
    except Exception as e:
        print(f"Error searching content: {e}")
        return []

def delete_record(url: str) -> bool:
    """Delete a specific record by URL"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crawled_data WHERE url = ?", (url,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting record: {e}")
        return False

def update_record(url: str, **fields) -> bool:
    """Update specific fields of a record"""
    check_db_path()
    valid_fields = {
        'html', 'cleaned_html', 'markdown', 'extracted_content', 
        'success', 'media', 'links', 'metadata', 'screenshot'
    }
    
    update_fields = {k: v for k, v in fields.items() if k in valid_fields}
    if not update_fields:
        return False
        
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        query = f"UPDATE crawled_data SET {set_clause} WHERE url = ?"
        
        values = list(update_fields.values())
        values.append(url)
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating record: {e}")
        return False

def get_records_by_status(success: bool, limit: int = 100) -> List[Dict]:
    """Get records filtered by success status"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT url, html, cleaned_html, markdown, extracted_content, success, media, links, metadata, screenshot
            FROM crawled_data 
            WHERE success = ?
            LIMIT ?
            """,
            (success, limit)
        )
        columns = [description[0] for description in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting records by status: {e}")
        return []

def optimize_database():
    """Optimize the database by running VACUUM and analyzing tables"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        cursor.execute("ANALYZE crawled_data")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error optimizing database: {e}")
        return False

def check_database_integrity() -> bool:
    """Check database integrity and consistency"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()
        return result == "ok"
    except Exception as e:
        print(f"Error checking database integrity: {e}")
        return False

def get_database_size() -> int:
    """Get the current size of the database file in bytes"""
    check_db_path()
    try:
        return os.path.getsize(DB_PATH)
    except Exception as e:
        print(f"Error getting database size: {e}")
        return 0

def vacuum_database() -> bool:
    """Reclaim unused space and defragment the database"""
    check_db_path()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error vacuuming database: {e}")
        return False

if __name__ == "__main__":
    # Delete the existing database file
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
