from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from enum import Enum

class CacheMode(str, Enum):
    NONE = "none"
    MEMORY = "memory"
    DISK = "disk"

class CrawlResult(BaseModel):
    url: HttpUrl
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    def dict(self, *args, **kwargs) -> dict:
        """Convert to a dictionary with formatted data"""
        result = super().dict(*args, **kwargs)
        result["extracted_at"] = result["extracted_at"].isoformat()
        
        # Add word count if not present
        if "word_count" not in result.get("metadata", {}):
            result["metadata"]["word_count"] = len(self.content.split())
            
        return result
    
    def to_markdown(self) -> str:
        """Convert the result to a markdown format"""
        metadata_str = "\n".join([
            f"- **{key}**: {value}" 
            for key, value in self.metadata.items()
        ])
        
        return f"""# {self.title}

## Source URL
{self.url}

## Content
{self.content}

## Metadata
{metadata_str}

## Extraction Time
{self.extracted_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

    def to_json(self, include_metadata: bool = True) -> dict:
        """Convert to a JSON-friendly format with optional metadata"""
        result = {
            "url": str(self.url),
            "title": self.title,
            "content": self.content,
            "extracted_at": self.extracted_at.isoformat()
        }
        
        if include_metadata:
            result["metadata"] = self.metadata
            
        return result
    
    @property
    def word_count(self) -> int:
        """Get the word count of the content"""
        return len(self.content.split())
    
    @property
    def summary(self) -> str:
        """Get a brief summary of the result"""
        return f"Title: {self.title}\nWords: {self.word_count}\nURL: {self.url}"

class ExtractionOptions(BaseModel):
    min_words: int = Field(default=50, ge=0)
    include_metadata: bool = True
    format: str = Field(default="json", pattern="^(json|markdown)$")
    timeout: int = Field(default=20, ge=5, le=60)
    cache_mode: CacheMode = Field(default=CacheMode.MEMORY)

class CrawlTask(BaseModel):
    url: HttpUrl
    options: ExtractionOptions = Field(default_factory=ExtractionOptions)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"
    result: Optional[CrawlResult] = None
    error: Optional[str] = None
    
    def dict(self, *args, **kwargs) -> dict:
        """Convert to a dictionary with formatted timestamps"""
        result = super().dict(*args, **kwargs)
        result["created_at"] = result["created_at"].isoformat()
        return result
    
    @property
    def is_completed(self) -> bool:
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        return self.status == "failed"
    
    @property
    def duration(self) -> float:
        """Get task duration in seconds"""
        if self.result and self.result.extracted_at:
            return (self.result.extracted_at - self.created_at).total_seconds()
        return 0.0
