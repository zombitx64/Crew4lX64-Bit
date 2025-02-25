from flask import Flask, request, jsonify
import sys
sys.path.append('.')
from crawl4ai.crawl4ai.async_webcrawler import AsyncWebCrawler as WebCrawler
from crawl4ai.crawl4ai.database import (
    init_db, get_records_paginated, export_data, 
    get_crawl_statistics, delete_record
)
from crawl4ai.crawl4ai.async_configs import CrawlerRunConfig, BrowserConfig
import json
import os
# Configure static folder for Flask
app = Flask(__name__)
app.static_folder = 'static'
app.static_url_path = ''
init_db()

import asyncio

@app.route('/api/crawl', methods=['POST'])
async def start_crawl():
    data = request.json
    try:
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            ignore_https_errors=True
        )

        run_config = CrawlerRunConfig(
            wait_until="networkidle",
            page_timeout=30000,  # 30 seconds
            mean_delay=float(data['requestDelay']),  # Convert to float and access directly from data
            exclude_external_links=not data['followLinks'],  # Inverse of follow_links
            exclude_external_images=not data['extractImages'],  # Inverse of extract_images
            screenshot=data['takeScreenshots'],
            screenshot_wait_for=1.0,  # Wait 1 second before taking screenshot
            adjust_viewport_to_content=True,  # Adjust viewport to content size for better screenshots
            check_robots_txt=data['respectRobotsTxt'],
            respect_robots_txt=data['respectRobotsTxt'],  # Legacy support
            verbose=True,
            # Additional settings for better content extraction
            only_text=False,  # We want HTML structure for markdown
            prettiify=True,  # Clean HTML output
            keep_data_attributes=True,  # Keep data attributes that might contain useful info
            extract_metadata=True  # Get page metadata
        )

        crawler = WebCrawler(config=browser_config)
        async with crawler:  # This ensures proper browser initialization
            result = await crawler.arun(url=data['url'], config=run_config)
            return jsonify({'success': True, 'result': result.model_dump()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    results, total = get_records_paginated(page, per_page)
    return jsonify({
        'results': results,
        'total': total,
        'page': page,
        'per_page': per_page
    })

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    stats = get_crawl_statistics()
    return jsonify(stats)

@app.route('/api/export/<format>', methods=['GET'])
def export_results(format):
    if format not in ['json', 'csv', 'md']:
        return jsonify({'error': 'Invalid format'}), 400
        
    try:
        export_dir = os.path.join(app.static_folder, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f'crawl_results.{format}'
        filepath = os.path.join(export_dir, filename)
        export_data(filepath, format)
        
        # Return the URL path to download the file
        return jsonify({'success': True, 'filename': f'/exports/{filename}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/results/<path:url>', methods=['GET', 'DELETE'])
def manage_url(url):
    if request.method == 'DELETE':
        try:
            success = delete_record(url)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:  # GET
        try:
            results, _ = get_records_paginated(page=1, per_page=1)
            for result in results:
                if result['url'] == url:
                    # Format output for better viewing
                    formatted_result = {
                        'url': result['url'],
                        'success': result['success'],
                        'content': result.get('markdown', result.get('extracted_content', '')),
                        'screenshot': result.get('screenshot', ''),
                        'links': json.loads(result.get('links', '{}')),
                        'robots_txt_respected': True,  # This field is for display only
                        'metadata': json.loads(result.get('metadata', '{}'))
                    }
                    return jsonify(formatted_result)
            return jsonify({'error': 'URL not found'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# Serve static files
@app.route('/')
def serve_interface():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    config = Config()
    config.bind = ["localhost:5000"]
    config.use_reloader = True
    
    asyncio.run(serve(app, config))
