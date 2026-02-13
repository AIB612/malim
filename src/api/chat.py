"""
Chat API
RAG-powered Q&A for battery knowledge
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..analysis.rag_engine import RAGEngine

router = APIRouter(prefix="/chat")

# RAG engine singleton
_rag_engine: Optional[RAGEngine] = None


async def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
        await _rag_engine.initialize()
    return _rag_engine


# ============ Models ============

class ChatRequest(BaseModel):
    """Chat request"""
    question: str = Field(..., min_length=3, max_length=1000, example="Ist 85% SoH gut für ein 3 Jahre altes EV?")
    vehicle_id: Optional[str] = Field(default=None, description="Optional vehicle ID for context")
    language: str = Field(default="de", description="Response language (de/en/zh)")


class SourceDocument(BaseModel):
    """Source document reference"""
    id: str
    content: str
    score: Optional[float] = None
    doc_type: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response"""
    answer: str
    sources: List[SourceDocument]
    confidence: float
    tokens_used: int


class KnowledgeAddRequest(BaseModel):
    """Add knowledge request"""
    content: str = Field(..., min_length=10, max_length=10000)
    doc_type: str = Field(default="knowledge", example="faq")
    vehicle_id: Optional[str] = None


class KnowledgeAddResponse(BaseModel):
    """Add knowledge response"""
    document_id: str
    message: str


# ============ Endpoints ============

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question about EV batteries.
    
    Uses RAG (Retrieval-Augmented Generation) to provide
    accurate answers based on the knowledge base.
    
    Examples:
    - "Ist 85% SoH gut für ein 3 Jahre altes EV?"
    - "Wie kann ich die Batterielebensdauer verlängern?"
    - "Was bedeutet Schnellladen für die Batterie?"
    - "Wann sollte ich die Batterie ersetzen?"
    """
    try:
        rag = await get_rag_engine()
        response = await rag.ask(
            question=request.question,
            vehicle_id=request.vehicle_id
        )
        
        sources = [
            SourceDocument(
                id=doc.id,
                content=doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                score=doc.score,
                doc_type=doc.metadata.get("doc_type") if doc.metadata else None
            )
            for doc in response.sources
        ]
        
        return ChatResponse(
            answer=response.answer,
            sources=sources,
            confidence=response.confidence,
            tokens_used=response.tokens_used
        )
    
    except Exception as e:
        # Fallback response if RAG fails
        return ChatResponse(
            answer=f"Entschuldigung, ich konnte die Frage nicht verarbeiten. Fehler: {str(e)}",
            sources=[],
            confidence=0.0,
            tokens_used=0
        )


@router.post("/knowledge", response_model=KnowledgeAddResponse, status_code=201)
async def add_knowledge(request: KnowledgeAddRequest):
    """
    Add knowledge to the RAG system.
    
    Use this to expand the knowledge base with:
    - Battery FAQs
    - Technical documentation
    - Best practices
    - Vehicle-specific information
    """
    try:
        rag = await get_rag_engine()
        doc_id = await rag.add_knowledge(
            content=request.content,
            doc_type=request.doc_type,
            vehicle_id=request.vehicle_id
        )
        
        return KnowledgeAddResponse(
            document_id=doc_id,
            message="Knowledge added successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add knowledge: {str(e)}")


# ============ Pre-loaded Knowledge ============

BATTERY_KNOWLEDGE = [
    {
        "content": """State of Health (SoH) ist ein Mass für die aktuelle Kapazität einer Batterie 
        im Vergleich zu ihrer ursprünglichen Kapazität. Ein SoH von 100% bedeutet, dass die Batterie 
        ihre volle ursprüngliche Kapazität hat. Bei 80% SoH hat die Batterie noch 80% ihrer 
        ursprünglichen Kapazität. Die meisten EV-Hersteller gewähren Garantie bis 70-80% SoH.""",
        "doc_type": "faq"
    },
    {
        "content": """Schnellladen (DC Fast Charging) mit mehr als 50kW kann die Batteriealterung 
        beschleunigen, besonders wenn es häufig genutzt wird. Empfehlung: Schnellladen auf maximal 
        20-30% der Ladevorgänge beschränken. Für den Alltag ist AC-Laden (11-22kW) schonender.""",
        "doc_type": "best_practice"
    },
    {
        "content": """Optimale Ladegrenzen für Langlebigkeit: Halten Sie den Ladestand zwischen 
        20% und 80% für den Alltag. Laden Sie nur auf 100% wenn Sie die volle Reichweite benötigen. 
        Vermeiden Sie es, die Batterie längere Zeit unter 10% oder über 90% zu halten.""",
        "doc_type": "best_practice"
    },
    {
        "content": """Temperatur und Batterielebensdauer: Die optimale Betriebstemperatur liegt 
        zwischen 15-25°C. Extreme Kälte (<0°C) reduziert die Reichweite temporär. Extreme Hitze 
        (>35°C) kann die Batterie dauerhaft schädigen. Nutzen Sie die Vorkonditionierung.""",
        "doc_type": "technical"
    },
    {
        "content": """Schweizer EV-Markt: In der Schweiz beträgt die durchschnittliche jährliche 
        Fahrleistung etwa 12'000 km. Bei diesem Nutzungsprofil und normalem Ladeverhalten 
        (80% AC, 20% DC) kann eine moderne EV-Batterie 15-20 Jahre halten bevor sie 70% SoH erreicht.""",
        "doc_type": "market"
    }
]


@router.post("/knowledge/seed", response_model=dict)
async def seed_knowledge():
    """
    Seed the knowledge base with default battery information.
    
    Call this once to initialize the RAG system with basic knowledge.
    """
    try:
        rag = await get_rag_engine()
        added = 0
        
        for item in BATTERY_KNOWLEDGE:
            await rag.add_knowledge(
                content=item["content"],
                doc_type=item["doc_type"]
            )
            added += 1
        
        return {"message": f"Seeded {added} knowledge documents"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed knowledge: {str(e)}")
