from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.db.models import Ticket, User, TicketResponse, TicketStatus, TicketPriority, TicketCategory
from app.schemas.ticket import TicketCreate, TicketResponse as TicketResponseSchema, TicketUpdate
from app.schemas.user import UserResponse
from app.rag.retriever import ticket_retriever
from app.rag.generator import response_generator
from app.rag.embeddings import embedding_service
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=TicketResponseSchema)
async def create_ticket(
    ticket: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new support ticket"""
    try:
        # Auto-categorize ticket if enabled
        categorization = None
        if ticket.auto_categorize:
            categorization = response_generator.categorize_ticket(
                f"{ticket.title} {ticket.description}"
            )
        
        # Create ticket
        db_ticket = Ticket(
            title=ticket.title,
            description=ticket.description,
            user_id=current_user.id,
            category=TicketCategory(categorization['category'].lower()) if categorization else None,
            predicted_category=TicketCategory(categorization['category'].lower()) if categorization else None,
            category_confidence=categorization['confidence'] if categorization else None,
            auto_categorized=bool(categorization),
            priority=TicketPriority(ticket.priority) if ticket.priority else TicketPriority.MEDIUM,
            tags=ticket.tags,
            metadata=ticket.metadata
        )
        
        db.add(db_ticket)
        db.commit()
        db.refresh(db_ticket)
        
        # Generate embedding for the ticket
        ticket_text = f"{db_ticket.title} {db_ticket.description}"
        embedding = embedding_service.generate_embedding(ticket_text)
        
        # Store embedding (you would implement this based on your vector DB choice)
        # For now, we'll store in the database
        from app.db.models import TicketEmbedding
        ticket_embedding = TicketEmbedding(
            ticket_id=db_ticket.id,
            embedding_vector=embedding,
            embedding_model=embedding_service.model_name
        )
        db.add(ticket_embedding)
        db.commit()
        
        return db_ticket
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )

@router.get("/", response_model=List[TicketResponseSchema])
async def get_tickets(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TicketStatus] = None,
    category_filter: Optional[TicketCategory] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tickets for the current user"""
    query = db.query(Ticket)
    
    # Filter by user role
    if current_user.role.value == "customer":
        query = query.filter(Ticket.user_id == current_user.id)
    elif current_user.role.value == "agent":
        query = query.filter(Ticket.assigned_agent_id == current_user.id)
    # Admins can see all tickets
    
    # Apply filters
    if status_filter:
        query = query.filter(Ticket.status == status_filter)
    if category_filter:
        query = query.filter(Ticket.category == category_filter)
    
    tickets = query.offset(skip).limit(limit).all()
    return tickets

@router.get("/{ticket_id}", response_model=TicketResponseSchema)
async def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if (current_user.role.value == "customer" and ticket.user_id != current_user.id) or \
       (current_user.role.value == "agent" and ticket.assigned_agent_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ticket

@router.put("/{ticket_id}", response_model=TicketResponseSchema)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if current_user.role.value == "customer" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    for field, value in ticket_update.dict(exclude_unset=True).items():
        setattr(ticket, field, value)
    
    db.commit()
    db.refresh(ticket)
    return ticket

@router.post("/{ticket_id}/generate-response")
async def generate_ai_response(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate AI-powered response for a ticket"""
    if current_user.role.value not in ["agent", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and admins can generate responses"
        )
    
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    try:
        # Find similar tickets and relevant knowledge
        search_query = f"{ticket.title} {ticket.description}"
        search_results = ticket_retriever.hybrid_search(
            search_query, db, exclude_ticket_id=ticket_id
        )
        
        # Generate response
        response_data = response_generator.generate_response(
            ticket,
            search_results['similar_tickets'],
            search_results['relevant_knowledge']
        )
        
        # Create response record
        ticket_response = TicketResponse(
            ticket_id=ticket_id,
            agent_id=current_user.id,
            content=response_data['response'],
            is_ai_generated=True,
            confidence_score=response_data['confidence'],
            sources_used=response_data['sources']
        )
        
        db.add(ticket_response)
        db.commit()
        db.refresh(ticket_response)
        
        return {
            "response": response_data['response'],
            "confidence": response_data['confidence'],
            "sources": response_data['sources'],
            "should_escalate": response_data['should_escalate'],
            "response_id": ticket_response.id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )

@router.get("/{ticket_id}/similar")
async def get_similar_tickets(
    ticket_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get similar tickets for a given ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    try:
        search_query = f"{ticket.title} {ticket.description}"
        similar_tickets = ticket_retriever.find_similar_tickets(
            search_query, db, limit=limit, exclude_ticket_id=ticket_id
        )
        
        return {
            "similar_tickets": [
                {
                    "ticket_id": item['ticket'].id,
                    "title": item['ticket'].title,
                    "description": item['ticket'].description,
                    "status": item['ticket'].status.value,
                    "similarity": item['similarity']
                }
                for item in similar_tickets
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar tickets: {str(e)}"
        )

@router.post("/{ticket_id}/responses", response_model=dict)
async def add_response(
    ticket_id: int,
    response_content: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a response to a ticket"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Check permissions
    if current_user.role.value == "customer" and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        ticket_response = TicketResponse(
            ticket_id=ticket_id,
            agent_id=current_user.id,
            content=response_content,
            is_ai_generated=False
        )
        
        db.add(ticket_response)
        db.commit()
        db.refresh(ticket_response)
        
        return {"message": "Response added successfully", "response_id": ticket_response.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add response: {str(e)}"
        ) 