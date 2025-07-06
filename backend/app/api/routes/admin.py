from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db.models import User, Ticket, KnowledgeBase, UserRole
from app.schemas.user import UserResponse
from app.core.auth import get_current_user
from app.rag.embeddings import embedding_service

router = APIRouter()

def require_admin(current_user: User = Depends(get_current_user)):
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/stats")
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get system statistics"""
    total_tickets = db.query(Ticket).count()
    open_tickets = db.query(Ticket).filter(Ticket.status == "open").count()
    resolved_tickets = db.query(Ticket).filter(Ticket.status == "resolved").count()
    total_users = db.query(User).count()
    total_knowledge = db.query(KnowledgeBase).count()
    
    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets,
        "total_users": total_users,
        "total_knowledge_items": total_knowledge
    }

@router.post("/knowledge-base")
async def add_knowledge_item(
    title: str,
    content: str,
    category: str = None,
    tags: List[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Add knowledge base item"""
    try:
        # Create knowledge base item
        kb_item = KnowledgeBase(
            title=title,
            content=content,
            category=category,
            tags=tags,
            source_type="manual"
        )
        
        db.add(kb_item)
        db.commit()
        db.refresh(kb_item)
        
        # Generate embedding
        embedding = embedding_service.generate_embedding(f"{title} {content}")
        
        # Store embedding
        from app.db.models import KnowledgeEmbedding
        kb_embedding = KnowledgeEmbedding(
            knowledge_id=kb_item.id,
            embedding_vector=embedding,
            embedding_model=embedding_service.model_name
        )
        db.add(kb_embedding)
        db.commit()
        
        return {"message": "Knowledge base item added successfully", "id": kb_item.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add knowledge base item: {str(e)}"
        )

@router.delete("/knowledge-base/{kb_id}")
async def delete_knowledge_item(
    kb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete knowledge base item"""
    kb_item = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base item not found"
        )
    
    db.delete(kb_item)
    db.commit()
    
    return {"message": "Knowledge base item deleted successfully"}

@router.post("/assign-ticket")
async def assign_ticket(
    ticket_id: int,
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Assign ticket to agent"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    agent = db.query(User).filter(User.id == agent_id).first()
    if not agent or agent.role != UserRole.AGENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent"
        )
    
    ticket.assigned_agent_id = agent_id
    db.commit()
    
    return {"message": "Ticket assigned successfully"} 