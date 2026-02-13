"""
RAG Engine for Malim
Retrieval-Augmented Generation for battery knowledge Q&A
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from openai import AsyncAzureOpenAI, AsyncOpenAI

from ..adapters import get_vector_store
from ..adapters.base import Document
from ..config import get_settings, LLMProviderType

logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """Response from RAG engine"""
    answer: str
    sources: List[Document]
    confidence: float
    tokens_used: int


class RAGEngine:
    """
    Retrieval-Augmented Generation Engine for battery knowledge.
    
    Features:
    - Vector similarity search for relevant documents
    - Context-aware answer generation
    - Source attribution
    - Multi-language support (DE/EN/ZH)
    
    Knowledge domains:
    - Battery chemistry (NMC, LFP, etc.)
    - Degradation factors
    - Charging best practices
    - Swiss EV market specifics
    """
    
    SYSTEM_PROMPT = """Du bist ein Experte für Elektrofahrzeug-Batterien und hilfst Nutzern, 
ihre Batterie-Gesundheit zu verstehen. Antworte präzise und verständlich.

Kontext aus der Wissensdatenbank:
{context}

Regeln:
1. Basiere deine Antwort auf dem gegebenen Kontext
2. Wenn der Kontext nicht ausreicht, sage es ehrlich
3. Gib praktische Empfehlungen wenn möglich
4. Beziehe dich auf Schweizer Marktbedingungen wenn relevant
5. Antworte in der Sprache der Frage (DE/EN/ZH)
"""
    
    def __init__(self):
        self.settings = get_settings()
        self.vector_store = get_vector_store()
        self.llm_client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize RAG engine components"""
        if self._initialized:
            return
        
        # Initialize vector store
        await self.vector_store.initialize()
        
        # Initialize LLM client based on provider
        if self.settings.llm_provider == LLMProviderType.AZURE:
            self.llm_client = AsyncAzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_key,
                api_version="2024-02-15-preview"
            )
        elif self.settings.llm_provider == LLMProviderType.OPENAI:
            self.llm_client = AsyncOpenAI(
                api_key=self.settings.openai_api_key
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")
        
        self._initialized = True
        logger.info("RAG engine initialized")
    
    async def ask(
        self,
        question: str,
        vehicle_id: Optional[str] = None,
        top_k: int = 5
    ) -> RAGResponse:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            vehicle_id: Optional vehicle ID for context filtering
            top_k: Number of documents to retrieve
            
        Returns:
            RAGResponse with answer and sources
        """
        if not self._initialized:
            await self.initialize()
        
        # Generate embedding for question
        query_embedding = await self._get_embedding(question)
        
        # Search for relevant documents
        filter_metadata = {"vehicle_id": vehicle_id} if vehicle_id else None
        search_result = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Build context from retrieved documents
        context = self._build_context(search_result.documents)
        
        # Generate answer
        answer, tokens = await self._generate_answer(question, context)
        
        # Calculate confidence based on search scores
        confidence = self._calculate_confidence(search_result.documents)
        
        return RAGResponse(
            answer=answer,
            sources=search_result.documents,
            confidence=confidence,
            tokens_used=tokens
        )
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.settings.llm_provider == LLMProviderType.AZURE:
            response = await self.llm_client.embeddings.create(
                input=text,
                model=self.settings.azure_openai_embedding_deployment
            )
        else:
            response = await self.llm_client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
        
        return response.data[0].embedding
    
    def _build_context(self, documents: List[Document]) -> str:
        """Build context string from retrieved documents"""
        if not documents:
            return "Keine relevanten Informationen gefunden."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            score_str = f" (Relevanz: {doc.score:.2f})" if doc.score else ""
            context_parts.append(f"[{i}]{score_str}: {doc.content}")
        
        return "\n\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str) -> tuple[str, int]:
        """Generate answer using LLM"""
        system_prompt = self.SYSTEM_PROMPT.format(context=context)
        
        if self.settings.llm_provider == LLMProviderType.AZURE:
            model = self.settings.azure_openai_deployment
        else:
            model = "gpt-4"
        
        response = await self.llm_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        return answer, tokens
    
    def _calculate_confidence(self, documents: List[Document]) -> float:
        """Calculate confidence based on search results"""
        if not documents:
            return 0.0
        
        scores = [doc.score for doc in documents if doc.score is not None]
        if not scores:
            return 0.5
        
        # Average of top scores, weighted towards higher scores
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        
        return (avg_score * 0.6 + max_score * 0.4)
    
    async def add_knowledge(
        self,
        content: str,
        doc_type: str = "knowledge",
        vehicle_id: Optional[str] = None,
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add knowledge to the RAG system.
        
        Args:
            content: Document content
            doc_type: Type of document (knowledge, manual, faq, etc.)
            vehicle_id: Optional vehicle ID for filtering
            doc_id: Optional document ID
            
        Returns:
            Document ID
        """
        if not self._initialized:
            await self.initialize()
        
        # Generate embedding
        embedding = await self._get_embedding(content)
        
        # Create document
        import uuid
        doc = Document(
            id=doc_id or str(uuid.uuid4()),
            content=content,
            embedding=embedding,
            metadata={
                "doc_type": doc_type,
                "vehicle_id": vehicle_id
            }
        )
        
        # Add to vector store
        ids = await self.vector_store.add_documents([doc])
        
        logger.info(f"Added knowledge document: {ids[0]}")
        return ids[0]
    
    async def close(self) -> None:
        """Close RAG engine resources"""
        if self.vector_store:
            await self.vector_store.close()
        self._initialized = False
