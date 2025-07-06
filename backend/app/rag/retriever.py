from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Ticket, KnowledgeBase, TicketEmbedding, KnowledgeEmbedding
from app.rag.embeddings import embedding_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TicketRetriever:
    """Retrieves similar tickets and knowledge base items"""
    
    def __init__(self):
        self.embedding_service = embedding_service
    
    def find_similar_tickets(self, query: str, db: Session, 
                           limit: int = None, 
                           exclude_ticket_id: int = None) -> List[Dict[str, Any]]:
        """Find similar tickets based on query"""
        if limit is None:
            limit = settings.MAX_RETRIEVED_DOCS
        
        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Get all ticket embeddings
            ticket_embeddings_query = db.query(TicketEmbedding).join(Ticket)
            
            if exclude_ticket_id:
                ticket_embeddings_query = ticket_embeddings_query.filter(
                    Ticket.id != exclude_ticket_id
                )
            
            ticket_embeddings = ticket_embeddings_query.all()
            
            if not ticket_embeddings:
                return []
            
            # Calculate similarities
            similarities = []
            for te in ticket_embeddings:
                similarity = self.embedding_service.calculate_similarity(
                    query_embedding, te.embedding_vector
                )
                
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    similarities.append({
                        'ticket_id': te.ticket_id,
                        'similarity': similarity,
                        'ticket_embedding': te
                    })
            
            # Sort by similarity
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Get ticket details
            similar_tickets = []
            for sim in similarities[:limit]:
                ticket = db.query(Ticket).filter(Ticket.id == sim['ticket_id']).first()
                if ticket:
                    similar_tickets.append({
                        'ticket': ticket,
                        'similarity': sim['similarity']
                    })
            
            return similar_tickets
            
        except Exception as e:
            logger.error(f"Failed to find similar tickets: {e}")
            return []
    
    def find_relevant_knowledge(self, query: str, db: Session, 
                              limit: int = None,
                              category: str = None) -> List[Dict[str, Any]]:
        """Find relevant knowledge base items"""
        if limit is None:
            limit = settings.MAX_RETRIEVED_DOCS
        
        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Get knowledge base embeddings
            kb_embeddings_query = db.query(KnowledgeEmbedding).join(KnowledgeBase)
            
            if category:
                kb_embeddings_query = kb_embeddings_query.filter(
                    KnowledgeBase.category == category
                )
            
            kb_embeddings_query = kb_embeddings_query.filter(
                KnowledgeBase.is_active == True
            )
            
            kb_embeddings = kb_embeddings_query.all()
            
            if not kb_embeddings:
                return []
            
            # Calculate similarities
            similarities = []
            for ke in kb_embeddings:
                similarity = self.embedding_service.calculate_similarity(
                    query_embedding, ke.embedding_vector
                )
                
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    similarities.append({
                        'knowledge_id': ke.knowledge_id,
                        'similarity': similarity,
                        'knowledge_embedding': ke
                    })
            
            # Sort by similarity
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Get knowledge base details
            relevant_knowledge = []
            for sim in similarities[:limit]:
                knowledge = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id == sim['knowledge_id']
                ).first()
                if knowledge:
                    relevant_knowledge.append({
                        'knowledge': knowledge,
                        'similarity': sim['similarity']
                    })
            
            return relevant_knowledge
            
        except Exception as e:
            logger.error(f"Failed to find relevant knowledge: {e}")
            return []
    
    def hybrid_search(self, query: str, db: Session, 
                     limit: int = None,
                     exclude_ticket_id: int = None) -> Dict[str, Any]:
        """Perform hybrid search across tickets and knowledge base"""
        if limit is None:
            limit = settings.MAX_RETRIEVED_DOCS
        
        # Split limit between tickets and knowledge
        ticket_limit = limit // 2
        knowledge_limit = limit - ticket_limit
        
        similar_tickets = self.find_similar_tickets(
            query, db, ticket_limit, exclude_ticket_id
        )
        
        relevant_knowledge = self.find_relevant_knowledge(
            query, db, knowledge_limit
        )
        
        return {
            'similar_tickets': similar_tickets,
            'relevant_knowledge': relevant_knowledge,
            'total_results': len(similar_tickets) + len(relevant_knowledge)
        }

# Global retriever instance
ticket_retriever = TicketRetriever() 