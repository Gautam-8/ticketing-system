from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"

class TicketPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketCategory(enum.Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    PRODUCT = "product"
    GENERAL = "general"

class UserRole(enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    tickets = relationship("Ticket", back_populates="user")
    responses = relationship("TicketResponse", back_populates="agent")

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), default=TicketPriority.MEDIUM)
    category = Column(Enum(TicketCategory))
    
    # Auto-categorization fields
    predicted_category = Column(Enum(TicketCategory))
    category_confidence = Column(Float)
    auto_categorized = Column(Boolean, default=False)
    
    # User information
    user_id = Column(Integer, ForeignKey("users.id"))
    assigned_agent_id = Column(Integer, ForeignKey("users.id"))
    
    # Metadata
    tags = Column(JSON)  # Store tags as JSON array
    metadata = Column(JSON)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="tickets", foreign_keys=[user_id])
    assigned_agent = relationship("User", foreign_keys=[assigned_agent_id])
    responses = relationship("TicketResponse", back_populates="ticket")
    embeddings = relationship("TicketEmbedding", back_populates="ticket")

class TicketResponse(Base):
    __tablename__ = "ticket_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    agent_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    
    # AI-generated response fields
    is_ai_generated = Column(Boolean, default=False)
    confidence_score = Column(Float)
    sources_used = Column(JSON)  # References to knowledge base or similar tickets
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="responses")
    agent = relationship("User", back_populates="responses")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100))
    tags = Column(JSON)
    
    # Metadata
    source_type = Column(String(50))  # FAQ, documentation, manual, etc.
    source_url = Column(String(500))
    version = Column(String(20))
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    embeddings = relationship("KnowledgeEmbedding", back_populates="knowledge_item")

class TicketEmbedding(Base):
    __tablename__ = "ticket_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    embedding_vector = Column(JSON)  # Store as JSON array
    embedding_model = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ticket = relationship("Ticket", back_populates="embeddings")

class KnowledgeEmbedding(Base):
    __tablename__ = "knowledge_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    knowledge_id = Column(Integer, ForeignKey("knowledge_base.id"))
    embedding_vector = Column(JSON)  # Store as JSON array
    embedding_model = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    knowledge_item = relationship("KnowledgeBase", back_populates="embeddings")

class TicketInteraction(Base):
    __tablename__ = "ticket_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Interaction details
    interaction_type = Column(String(50))  # view, comment, rate, etc.
    interaction_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemMetrics(Base):
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float)
    metric_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 