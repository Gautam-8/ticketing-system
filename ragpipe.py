import os
import chromadb
import requests
from sentence_transformers import SentenceTransformer
from chromadb.config import Settings
from typing import Mapping
import json


class RAGPipeline:
    def __init__(self, persist_dir="ticket_db"):
        self.persist_dir = persist_dir
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Main Chroma client
        self.client = chromadb.Client(Settings(
            persist_directory=self.persist_dir,
            anonymized_telemetry=False
        ))

        # Ticket collection
        self.collection = self.client.get_or_create_collection(name="support_tickets")

        # KB collection (separate)
        self.kb_collection = self.client.get_or_create_collection(name="kb_docs")

    def reset_support_tickets(self):
        self.collection.delete(where={"id": {"$ne": ""}})
        if os.path.exists("tickets.jsonl"):
            open("tickets.jsonl", "w").close()
    
    # Clear ticket logs
    if os.path.exists("tickets.jsonl"):
        open("tickets.jsonl", "w").close()


    def embed_text(self, text):
        return self.embed_model.encode(text).tolist()

    def chunk_text(self, text, chunk_size=300, overlap=50):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def store_ticket(self, ticket_id, text, category, response, score, is_confident):
        embedding = self.embed_text(text)
        self.collection.add(
            documents=[text],
            metadatas=[{"category": category}],
            ids=[ticket_id],
            embeddings=[embedding]
        )

        # ✅ Save for dashboard
        log = {
            "id": ticket_id,
            "text": text,
            "category": category,
            "response": response,
            "confidence": score,
            "escalate": not is_confident,
        }
        with open("tickets.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log) + "\n")

    def get_all_tickets(self):
        tickets = []
        if os.path.exists("tickets.jsonl"):
            with open("tickets.jsonl", "r", encoding="utf-8") as f:
                for line in f:
                    tickets.append(json.loads(line))
        return tickets[::-1]  # Show latest first


    def index_uploaded_kb(self, text: str, source_name: str = "uploaded_doc.txt"):
        chunks = self.chunk_text(text)
        embeddings = [self.embed_text(chunk) for chunk in chunks]

        ids = [f"{source_name}_{i}" for i in range(len(chunks))]
        metadatas: list[Mapping[str, str]] = [{"source": source_name} for _ in chunks]

        self.kb_collection.add(
            documents=chunks,
            metadatas=metadatas,  # type: ignore
            ids=ids,
            embeddings=embeddings
        )

    def search_similar(self, query, top_k=3):
        query_embedding = self.embed_text(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["distances", "documents", "metadatas"]
        )
        return results

    def search_kb(self, query, top_k=3):
        query_embedding = self.embed_text(query)
        results = self.kb_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents"]
        )
        return results

    def generate_response(self, query: str, top_k=3, threshold=0.7):
        # Past ticket retrieval
        ticket_results = self.search_similar(query, top_k)
        ticket_docs = ticket_results["documents"][0] if ticket_results["documents"] else []
        distances = ticket_results["distances"][0] if ticket_results["distances"] else []
        scores = [1 - d for d in distances]
        avg_score = sum(scores) / len(scores) if scores else 0

        # KB retrieval
        kb_results = self.search_kb(query, top_k)
        kb_docs = kb_results["documents"][0] if kb_results["documents"] else []
        print("kb_docs :: ", kb_docs)

        # Combine both
        combined_context = "\n".join(f"- {doc}" for doc in ticket_docs + kb_docs)

        prompt = f"""You are a helpful support assistant.
Use the information below from past tickets and company documentation to help the user.

User Question: "{query}"

Relevant Information:
{combined_context}

Helpful Response:"""

        response = requests.post("http://localhost:1234/v1/chat/completions", json={
            "model": "your-model-name",  # replace if needed
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        })

        result = response.json()
        reply = result["choices"][0]["message"]["content"]

        is_confident = avg_score >= threshold
        return reply, avg_score, is_confident
