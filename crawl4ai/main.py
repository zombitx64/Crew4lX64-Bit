import asyncio, os
from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, PlainTextResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, Security

from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any, Union
import psutil
import time
import uuid
import math
import logging
from enum import Enum
from dataclasses import dataclass
from crawl4ai import AsyncWebCrawler, CrawlResult, CacheMode, ExtractionOptions
from crawl4ai.config import MIN_WORD_THRESHOLD
from crawl4ai.extraction_strategy import ExtractionStrategy

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TaskInfo:
    task_id: str
    status: TaskStatus
    result: Union[CrawlResult, List[CrawlResult], None] = None
    error: Optional[str] = None

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}

    def create_task(self) -> TaskInfo:
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(task_id=task_id, status=TaskStatus.PENDING)
        self.tasks[task_id] = task_info
        return task_info

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        return self.tasks.get(task_id)

class CrawlerService:
    def __init__(self):
        self.task_manager = TaskManager()
        self.crawler = AsyncWebCrawler()

    async def start(self):
        """Initialize any required resources"""
        pass

    async def stop(self):
        """Cleanup resources"""
        pass

    async def submit_task(self, request: 'CrawlRequest') -> str:
        task_info = self.task_manager.create_task()
        asyncio.create_task(self._process_task(task_info, request))
        return task_info.task_id

    async def _process_task(self, task_info: TaskInfo, request: 'CrawlRequest'):
        try:
            task_info.status = TaskStatus.PROCESSING
            try:
                async with AsyncWebCrawler(
                    config={
                        "timeout": 20,  # Shorter timeout
                        "javascript": True,  # Enable JavaScript
                        "wait_until": "networkidle",  # Wait for network to be idle
                        "cache_mode": CacheMode.MEMORY,  # Use memory caching
                        "max_retries": 2  # Limit retries
                    }
                ) as crawler:
                    try:
                        result = await asyncio.wait_for(
                            crawler.arun(
                                url=request.url,
                                strategy=ExtractionStrategy(request.strategy),
                                word_count_threshold=request.word_count_threshold
                            ),
                            timeout=20.0
                        )
                        
                        if not result or (isinstance(result, list) and len(result) == 0):
                            raise Exception("No content extracted from the page")
                            
                        task_info.result = result
                        task_info.status = TaskStatus.COMPLETED
                        
                    except asyncio.TimeoutError:
                        task_info.status = TaskStatus.FAILED
                        task_info.error = "Crawling timeout: Page took too long to load or process"
                        
            except Exception as e:
                task_info.status = TaskStatus.FAILED
                task_info.error = f"Crawler error: {str(e)}"
                logger.error(f"Crawler error for URL {request.url}: {str(e)}", exc_info=True)
                
        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error = f"System error: {str(e)}"
            logger.error(f"System error in task processing: {str(e)}", exc_info=True)

class CrawlRequest(BaseModel):
    url: HttpUrl
    strategy: str = Field(default="rule_based", pattern="^(llm|rule_based|hybrid)$")
    word_count_threshold: int = Field(default=MIN_WORD_THRESHOLD, ge=50)

# Initialize crawler service
crawler_service = CrawlerService()

app = FastAPI(title="Crawl4AI API")

# CORS configuration
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API token security
security = HTTPBearer()
CRAWL4AI_API_TOKEN = os.getenv("CRAWL4AI_API_TOKEN")

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not CRAWL4AI_API_TOKEN:
        return credentials
    if credentials.credentials != CRAWL4AI_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials

def secure_endpoint():
    return Depends(verify_token) if CRAWL4AI_API_TOKEN else None

# Lifespan events
@app.on_event("startup")
async def startup():
    await crawler_service.start()

@app.on_event("shutdown")
async def shutdown():
    await crawler_service.stop()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.post("/crawl", dependencies=[secure_endpoint()] if CRAWL4AI_API_TOKEN else [])
async def crawl(request: CrawlRequest) -> Dict[str, str]:
    task_id = await crawler_service.submit_task(request)
    return {"task_id": task_id}

@app.get("/task/{task_id}", dependencies=[secure_endpoint()] if CRAWL4AI_API_TOKEN else [])
async def get_task_status(task_id: str, response: Response):
    task_info = crawler_service.task_manager.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")

    response_data = {
        "status": task_info.status,
        "task_id": task_id
    }

    if task_info.status == TaskStatus.COMPLETED:
        accept = response.headers.get("Accept", "")
        
        # Handle markdown format
        if "text/markdown" in accept:
            response.headers["Content-Type"] = "text/markdown; charset=utf-8"
            if isinstance(task_info.result, list):
                return "# Crawling Results\n\n" + "\n\n---\n\n".join(
                    [result.to_markdown() for result in task_info.result]
                )
            return task_info.result.to_markdown()
        
        # Handle JSON format (default)
        if isinstance(task_info.result, list):
            response_data["results"] = [result.dict() for result in task_info.result]
        else:
            response_data["result"] = task_info.result.dict() if task_info.result else None
            
    elif task_info.status == TaskStatus.FAILED:
        response_data["error"] = task_info.error
        response_data["error_details"] = {
            "message": task_info.error,
            "time": time.time()
        }
    
    return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=11235)
