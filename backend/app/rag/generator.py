from typing import List, Dict, Any, Optional
import openai
from app.core.config import settings
from app.db.models import Ticket, KnowledgeBase
import logging

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Generates AI-powered responses for tickets using RAG"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def generate_response(self, ticket: Ticket, 
                         similar_tickets: List[Dict[str, Any]] = None,
                         relevant_knowledge: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate AI response for a ticket"""
        try:
            # Build context from similar tickets and knowledge
            context = self._build_context(similar_tickets, relevant_knowledge)
            
            # Create prompt
            prompt = self._create_prompt(ticket, context)
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            generated_text = response.choices[0].message.content
            
            # Calculate confidence score (simplified)
            confidence = self._calculate_confidence(
                similar_tickets, relevant_knowledge, response
            )
            
            return {
                'response': generated_text,
                'confidence': confidence,
                'sources': self._extract_sources(similar_tickets, relevant_knowledge),
                'should_escalate': confidence < settings.ESCALATION_THRESHOLD
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return {
                'response': "I apologize, but I'm unable to generate a response at this time. Please contact a human agent for assistance.",
                'confidence': 0.0,
                'sources': [],
                'should_escalate': True
            }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the AI assistant"""
        return """You are a helpful customer support assistant. Your role is to:
        1. Provide accurate and helpful responses to customer inquiries
        2. Use the provided context from similar tickets and knowledge base
        3. Be empathetic and professional
        4. If you're unsure about something, acknowledge it and suggest escalation
        5. Keep responses concise but comprehensive
        6. Always prioritize customer satisfaction and safety"""
    
    def _create_prompt(self, ticket: Ticket, context: str) -> str:
        """Create prompt for response generation"""
        prompt = f"""
        Customer Ticket:
        Title: {ticket.title}
        Description: {ticket.description}
        Category: {ticket.category.value if ticket.category else 'Unknown'}
        Priority: {ticket.priority.value if ticket.priority else 'Unknown'}
        
        Context from similar tickets and knowledge base:
        {context}
        
        Please provide a helpful response to this customer ticket. Use the context provided to give accurate information, but don't directly reference the context in your response. Be professional, empathetic, and solution-focused.
        """
        
        return prompt
    
    def _build_context(self, similar_tickets: List[Dict[str, Any]] = None,
                      relevant_knowledge: List[Dict[str, Any]] = None) -> str:
        """Build context string from similar tickets and knowledge"""
        context_parts = []
        
        if similar_tickets:
            context_parts.append("Similar resolved tickets:")
            for i, item in enumerate(similar_tickets[:3], 1):
                ticket = item['ticket']
                similarity = item['similarity']
                context_parts.append(f"{i}. Title: {ticket.title}")
                context_parts.append(f"   Description: {ticket.description}")
                context_parts.append(f"   Status: {ticket.status.value}")
                context_parts.append(f"   Similarity: {similarity:.2f}")
                context_parts.append("")
        
        if relevant_knowledge:
            context_parts.append("Relevant knowledge base articles:")
            for i, item in enumerate(relevant_knowledge[:3], 1):
                knowledge = item['knowledge']
                similarity = item['similarity']
                context_parts.append(f"{i}. Title: {knowledge.title}")
                context_parts.append(f"   Content: {knowledge.content}")
                context_parts.append(f"   Category: {knowledge.category}")
                context_parts.append(f"   Similarity: {similarity:.2f}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _calculate_confidence(self, similar_tickets: List[Dict[str, Any]] = None,
                            relevant_knowledge: List[Dict[str, Any]] = None,
                            response: Any = None) -> float:
        """Calculate confidence score for the generated response"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on similar tickets
        if similar_tickets:
            avg_similarity = sum(item['similarity'] for item in similar_tickets) / len(similar_tickets)
            confidence += avg_similarity * 0.3
        
        # Increase confidence based on relevant knowledge
        if relevant_knowledge:
            avg_similarity = sum(item['similarity'] for item in relevant_knowledge) / len(relevant_knowledge)
            confidence += avg_similarity * 0.2
        
        # Ensure confidence is between 0 and 1
        return min(max(confidence, 0.0), 1.0)
    
    def _extract_sources(self, similar_tickets: List[Dict[str, Any]] = None,
                        relevant_knowledge: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract source information for the response"""
        sources = []
        
        if similar_tickets:
            for item in similar_tickets:
                sources.append({
                    'type': 'ticket',
                    'id': item['ticket'].id,
                    'title': item['ticket'].title,
                    'similarity': item['similarity']
                })
        
        if relevant_knowledge:
            for item in relevant_knowledge:
                sources.append({
                    'type': 'knowledge',
                    'id': item['knowledge'].id,
                    'title': item['knowledge'].title,
                    'similarity': item['similarity']
                })
        
        return sources
    
    def categorize_ticket(self, ticket_text: str) -> Dict[str, Any]:
        """Automatically categorize a ticket"""
        try:
            prompt = f"""
            Analyze this customer support ticket and categorize it:
            
            Ticket: {ticket_text}
            
            Categories:
            - TECHNICAL: Technical issues, bugs, software problems
            - BILLING: Payment, subscription, billing inquiries
            - ACCOUNT: Account access, profile, settings
            - PRODUCT: Product information, features, usage
            - GENERAL: General inquiries, feedback
            
            Respond with only the category name and confidence (0-1):
            Format: CATEGORY_NAME,confidence_score
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a ticket categorization system. Respond only with the category and confidence score."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            category, confidence = result.split(',')
            
            return {
                'category': category.strip(),
                'confidence': float(confidence.strip())
            }
            
        except Exception as e:
            logger.error(f"Failed to categorize ticket: {e}")
            return {
                'category': 'GENERAL',
                'confidence': 0.5
            }

# Global generator instance
response_generator = ResponseGenerator() 