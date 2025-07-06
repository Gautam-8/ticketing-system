from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"

class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    PRODUCT = "product"
    GENERAL = "general"

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    priority: Optional[TicketPriority] = TicketPriority.MEDIUM
    category: Optional[TicketCategory] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    auto_categorize: bool = True

class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    assigned_agent_id: Optional[int] = None

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: Optional[TicketCategory]
    predicted_category: Optional[TicketCategory]
    category_confidence: Optional[float]
    auto_categorized: bool
    user_id: int
    assigned_agent_id: Optional[int]
    tags: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

class TicketResponseCreate(BaseModel):
    content: str = Field(..., min_length=1)
    
class TicketResponseResponse(BaseModel):
    id: int
    ticket_id: int
    agent_id: int
    content: str
    is_ai_generated: bool
    confidence_score: Optional[float]
    sources_used: Optional[List[Dict[str, Any]]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True 