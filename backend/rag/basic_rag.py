"""
Basic RAG — Baseline Implementation
Vector similarity search → top-K chunks → LLM prompt

This is the BASELINE we're beating. No graph. No structure.
Just cosine similarity over document chunks.
"""

import os
import time
import logging
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import faiss
from dotenv import load_dotenv

from ..llm.gemini_client import gemini_generate

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

TOP_K = int(os.getenv("TOP_K_BASIC_RAG", 5))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 384  # sentence-transformers all-MiniLM-L6-v2

_sentence_transformer = None
USE_SENTENCE_TRANSFORMERS = os.getenv("USE_SENTENCE_TRANSFORMERS", "true").lower() == "true"


# Gemini calls go through shared gemini_client.gemini_generate()


def _get_sentence_transformer():
    """Lazily load sentence-transformer for local embeddings."""
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Loaded sentence-transformers for local embeddings (384 dims)")
        except ImportError:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
            _sentence_transformer = False
    return _sentence_transformer if _sentence_transformer else None


@dataclass
class RAGResult:
    answer: str
    retrieved_chunks: list[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    method: str = "basic_rag"


class BasicRAG:
    """
    Standard RAG pipeline:
    1. Embed query
    2. Cosine similarity search over FAISS index
    3. Concatenate top-K chunks
    4. Send to LLM
    
    This is the BASELINE. Expensive. Indiscriminate. 
    No structural understanding of relationships.
    """

    def __init__(self):
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product = cosine similarity
        self.chunks: list[str] = []
        self.chunk_metadata: list[dict] = []
        
        # Try to load pre-built FAISS index from disk
        # Use absolute path: work up from this file → backend → graphrag-hackathon → data
        faiss_path = Path(__file__).resolve().parent.parent.parent / "data" / "faiss_index.pkl"
        
        logger.info(f"Attempting to load FAISS index from: {faiss_path}")
        logger.info(f"Path exists: {faiss_path.exists()}")
        
        if faiss_path.exists():
            try:
                import pickle
                with open(faiss_path, "rb") as f:
                    data = pickle.load(f)
                    self.index = data["index"]
                    self.chunks = data["chunks"]
                    self.chunk_metadata = data.get("metadata", [])
                logger.info(f"✅ Loaded FAISS index from {faiss_path} ({len(self.chunks)} chunks, {self.index.ntotal} vectors)")
            except Exception as e:
                logger.error(f"❌ Failed to load FAISS index: {e}", exc_info=True)
                # Fall through to build from sample docs
                self._build_index_from_sample_docs()
        else:
            logger.warning(f"⚠️  FAISS index not found at {faiss_path}. Building from sample documents...")
            self._build_index_from_sample_docs()

    def _build_index_from_sample_docs(self):
        """Dynamically build FAISS index from sample documents with semantic chunking"""
        sample_docs_dir = Path(__file__).resolve().parent.parent.parent / "data" / "sample_docs"
        
        if not sample_docs_dir.exists():
            logger.warning(f"Sample docs directory not found at {sample_docs_dir}")
            return
        
        # Load all .md and .txt files
        doc_files = list(sample_docs_dir.glob("*.md")) + list(sample_docs_dir.glob("*.txt"))
        if not doc_files:
            logger.warning(f"No documents found in {sample_docs_dir}")
            return
        
        logger.info(f"Loading {len(doc_files)} documents from {sample_docs_dir}...")
        
        for doc_file in doc_files:
            try:
                with open(doc_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # Semantic chunking: split by sections and paragraphs
                sections = content.split("##")
                for section_idx, section in enumerate(sections):
                    # Split each section into paragraphs
                    paragraphs = section.split("\n\n")
                    
                    # Group smaller paragraphs together, keep larger ones separate
                    current_chunk = ""
                    for para in paragraphs:
                        para = para.strip()
                        if not para:
                            continue
                        
                        if len(current_chunk) + len(para) < 1000:  # Combine paragraphs up to 1000 chars
                            if current_chunk:
                                current_chunk += "\n\n"
                            current_chunk += para
                        else:
                            if current_chunk:
                                self.chunks.append(current_chunk)
                                self.chunk_metadata.append({
                                    "source": doc_file.name,
                                    "section": section_idx,
                                })
                            current_chunk = para
                    
                    if current_chunk:
                        self.chunks.append(current_chunk)
                        self.chunk_metadata.append({
                            "source": doc_file.name,
                            "section": section_idx,
                        })
                
                logger.info(f"  ✅ Loaded {doc_file.name} ({len(content)} chars → {len([c for c in self.chunks if c.split('###')[0].startswith(doc_file.name.split('.')[0][:20])])} semantic chunks)")
            except Exception as e:
                logger.warning(f"Failed to load {doc_file.name}: {e}")
        
        # Embed all chunks
        if self.chunks:
            try:
                logger.info(f"Embedding {len(self.chunks)} chunks...")
                embeddings = self._embed_batch(self.chunks)
                vectors = np.array(embeddings, dtype="float32")
                faiss.normalize_L2(vectors)
                self.index.add(vectors)
                logger.info(f"✅ Built FAISS index with {self.index.ntotal} vectors from {len(self.chunks)} chunks")
            except Exception as e:
                logger.error(f"Failed to embed chunks: {e}")
                self.chunks = []  # Clear on failure
        else:
            logger.warning("No chunks extracted from documents")

    def add_documents(self, chunks: list[str], metadata: list[dict] = None):
        """Add document chunks to the FAISS index."""
        if not chunks:
            return
        logger.info(f"Embedding {len(chunks)} chunks for FAISS index...")
        embeddings = self._embed_batch(chunks)
        vectors = np.array(embeddings, dtype="float32")
        # Normalize for cosine similarity
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.chunks.extend(chunks)
        self.chunk_metadata.extend(metadata or [{} for _ in chunks])
        logger.info(f"FAISS index now has {self.index.ntotal} vectors")

    def query(self, question: str, top_k: int = TOP_K) -> RAGResult:
        """
        Full RAG pipeline for a single question.
        Returns answer + full token accounting.
        """
        t0 = time.time()

        # 1. Embed the query
        try:
            query_embedding = self._embed(question)
            if not query_embedding or len(query_embedding) == 0:
                raise ValueError("Empty embedding returned")
            query_vec = np.array([query_embedding], dtype="float32")
            faiss.normalize_L2(query_vec)
        except Exception as e:
            logger.error(f"Embedding failed: {e}. Using fallback retrieval.")
            query_vec = None

        # 2. Retrieve top-K similar chunks
        retrieved = []
        if query_vec is not None and self.index.ntotal > 0:
            try:
                distances, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))
                retrieved = [self.chunks[i] for i in indices[0] if i < len(self.chunks)]
                logger.info(f"✅ Retrieved {len(retrieved)} chunks from FAISS (ntotal: {self.index.ntotal})")
            except Exception as e:
                logger.error(f"FAISS search failed: {e}. Falling back to first chunks.")
                retrieved = self.chunks[:top_k]
        elif self.chunks:
            # Fallback: return first K chunks if embedding/search fails
            logger.warning(f"⚠️ Embedding or index unavailable. Using first {top_k} chunks as fallback.")
            retrieved = self.chunks[:top_k]
        else:
            retrieved = ["[No documents available. Please ingest documents first.]"]

        # 3. Build context (this is where tokens pile up)
        context = "\n\n---\n\n".join(retrieved)

        # 4. Build prompt
        system_prompt = (
            "You are an assistant grounded in provided documents. Answer based ONLY on the context. "
            "Cite sources from the context. If context is insufficient, acknowledge it."
        )
        user_prompt = f"""Context from documents:
{context}

Question: {question}

Based on the context above, provide a comprehensive answer with citations:"""

        # 5. Call Gemini via shared client (accurate token counts)
        result = gemini_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=1500,
        )

        latency_ms = (time.time() - t0) * 1000

        return RAGResult(
            answer=result["answer"],
            retrieved_chunks=retrieved,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=result["total_tokens"],
            latency_ms=latency_ms,
            method="basic_rag",
        )

    def _embed(self, text: str) -> list[float]:
        """Embed a single text string using OpenAI, then sentence-transformers, then zeros."""
        # Try OpenAI first
        try:
            from openai import OpenAI
            openai_client = OpenAI()
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text[:8191],
            )
            return response.data[0].embedding
        except Exception as e:
            logger.debug(f"OpenAI embedding failed: {e}")
        
        # Try sentence-transformers
        if USE_SENTENCE_TRANSFORMERS:
            try:
                model = _get_sentence_transformer()
                if model:
                    embedding = model.encode(text[:8191])
                    return embedding.tolist()
            except Exception as e:
                logger.debug(f"Sentence-transformers embedding failed: {e}")
        
        # Fallback to zeros
        logger.warning("Falling back to zero embeddings")
        return [0.0] * 384

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently using OpenAI, then sentence-transformers, then zeros."""
        # Try OpenAI first (batch of 100)
        try:
            from openai import OpenAI
            openai_client = OpenAI()
            all_embeddings = []
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=[t[:8191] for t in batch],
                )
                all_embeddings.extend([item.embedding for item in response.data])
            return all_embeddings
        except Exception as e:
            logger.debug(f"OpenAI batch embedding failed: {e}")
        
        # Try sentence-transformers (local, no API call)
        if USE_SENTENCE_TRANSFORMERS:
            try:
                model = _get_sentence_transformer()
                if model:
                    embeddings = model.encode([t[:8191] for t in texts])
                    return embeddings.tolist()
            except Exception as e:
                logger.debug(f"Sentence-transformers batch embedding failed: {e}")
        
        # Fallback to zeros
        logger.warning(f"Falling back to zero embeddings for {len(texts)} texts")
        return [[0.0] * 384 for _ in texts]

    def count_tokens(self, text: str) -> int:
        from ..llm.gemini_client import count_tokens_gemini
        return count_tokens_gemini(text)

    def get_index_stats(self) -> dict:
        return {
            "total_chunks": len(self.chunks),
            "index_size": self.index.ntotal,
            "embedding_dim": EMBEDDING_DIM,
        }
