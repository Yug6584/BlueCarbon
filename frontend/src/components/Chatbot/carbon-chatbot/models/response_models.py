from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Chunk:
    """Document chunk with metadata"""
    id: str
    text: str
    source_file: str
    page_number: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    similarity_score: Optional[float] = None

@dataclass
class Source:
    """Source information for citations"""
    filename: str
    snippet: str
    similarity_score: float
    chunk_id: str
    page_number: int = 0
    source_type: str = "uploaded"  # "uploaded", "web", or "knowledge_base"
    url: Optional[str] = None  # URL for web sources (makes them clickable)

@dataclass
class ChartSpec:
    """Chart specification for autonomous generation"""
    type: str  # "line", "bar", "pie", "scatter", "histogram"
    title: str
    x_label: str = ""
    y_label: str = ""
    data_refs: List[str] = field(default_factory=list)
    description: str = ""

@dataclass
class PlanningData:
    """Response planning data for multi-pass generation"""
    outline: List[str]
    need_charts: bool
    chart_specs: List[ChartSpec]
    response_type: str
    suggested_questions: List[str]
    estimated_length: str = "medium"  # "short", "medium", "long"
    sections: Dict[str, str] = field(default_factory=dict)

@dataclass
class Chart:
    """Generated chart data"""
    type: str
    title: str
    data: Dict[str, Any]
    image_base64: str
    caption: str
    file_path: str = ""

@dataclass
class VisualContentSummary:
    """Summary of visual content in response"""
    total_images: int = 0
    images_displayed: int = 0
    charts_generated: int = 0
    selection_method: str = "automatic"
    quality_score: float = 0.0
    ai_selected: bool = False

@dataclass
class SourcePriorityInfo:
    """Information about source prioritization"""
    uploaded_file_sources: int = 0
    general_knowledge_sources: int = 0
    web_search_sources: int = 0
    file_priority_percentage: float = 0.0
    prioritization_method: str = "standard"
    total_sources: int = 0
    session_files_available: int = 0

@dataclass
class ResponseData:
    """Complete response data structure"""
    answer: str
    sources: List[Source]
    charts: List[Chart] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    retrieval_time: float = 0.0
    generation_time: float = 0.0
    cached: bool = False
    response_type: str = "general"
    planning_data: Optional[PlanningData] = None
    confidence_score: float = 0.0
    web_images: List[Dict[str, Any]] = field(default_factory=list)
    visual_content_summary: Optional[VisualContentSummary] = None
    source_priority_info: Optional[SourcePriorityInfo] = None

@dataclass
class WebResult:
    """Web search result with image support"""
    title: str
    url: str
    snippet: str
    relevance_score: float
    source_type: str = "web"  # "web", "news", or "image"
    published_date: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None

@dataclass
class ProcessingStatus:
    """File processing status"""
    task_id: str
    status: str  # "processing", "completed", "failed"
    progress: float
    chunks_processed: int
    total_chunks: int = 0
    error_message: Optional[str] = None
    filename: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

@dataclass
class TranslationResult:
    """Translation result"""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    confidence: Optional[float] = None
    service_used: str = "libretranslate"

@dataclass
class ErrorResponse:
    """Error response structure"""
    error_type: str
    message: str
    suggestions: List[str] = field(default_factory=list)
    retry_possible: bool = True
    fallback_used: bool = False