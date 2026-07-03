"""
Basic RAG — Baseline Implementation
Vector similarity search → top-K chunks → LLM prompt

This is the BASELINE we're beating. No graph. No structure.
Just cosine similarity over document chunks.
"""

import os

# Force HuggingFace transformers to use the PyTorch backend only. Without this,
# transformers eagerly imports TensorFlow, which fails on this machine with a
# protobuf mismatch ("cannot import name 'runtime_version'") — breaking
# sentence-transformers and silently falling back to zero embeddings. Must be
# set before transformers is imported anywhere.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

import time
import logging
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import faiss
from dotenv import load_dotenv

from ..llm.gemini_client import (
    gemini_generate,
    MAX_OUTPUT_TOKENS,
    CONCISE_ANSWER_INSTRUCTION,
    count_context_tokens,
)

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
logger = logging.getLogger(__name__)

TOP_K = int((os.getenv("TOP_K_BASIC_RAG", "5") or "5").strip())
EMBEDDING_MODEL = (os.getenv("EMBEDDING_MODEL", "text-embedding-3-small") or "").strip()
EMBEDDING_DIM = 384  # sentence-transformers all-MiniLM-L6-v2

_sentence_transformer = None
USE_SENTENCE_TRANSFORMERS = (os.getenv("USE_SENTENCE_TRANSFORMERS", "true") or "true").lower().strip() == "true"

# Corpus directory (relative to project root). Defaults to the full arXiv bulk dataset.
RAG_DATA_DIR = (os.getenv("RAG_DATA_DIR", "data/arxiv_bulk") or "data/arxiv_bulk").strip()
# Load the full prebuilt arxiv index by default — the fair, dataset-scale baseline
# the hackathon requires (Basic RAG must run on the same large corpus as GraphRAG).
RAG_USE_PREBUILT_INDEX = (os.getenv("RAG_USE_PREBUILT_INDEX", "true") or "true").lower().strip() == "true"


def _assert_real_embeddings(vectors: np.ndarray) -> None:
    """Abort loudly if embeddings are degenerate (all-zero rows).

    The embedding stack silently falls back to zero vectors when neither OpenAI
    nor sentence-transformers is usable (e.g. torch fails to import). A FAISS
    index of zero vectors is useless — every similarity is identical — so we
    refuse to build/save it rather than waste a long ingest run.
    """
    if vectors.size == 0:
        raise RuntimeError("No embeddings produced — refusing to build an empty index.")

    zero_rows = int(np.count_nonzero(np.abs(vectors).sum(axis=1) == 0))
    if zero_rows == len(vectors):
        raise RuntimeError(
            f"All {len(vectors)} embeddings are zero vectors. The embedding backend "
            "failed silently (OpenAI key missing AND sentence-transformers/torch not "
            "importable). Fix the embedder, then re-run — refusing to write a useless "
            "zero-vector index."
        )
    if zero_rows:
        logger.warning(f"[WARN]  {zero_rows}/{len(vectors)} embeddings are zero vectors (some chunks failed to embed).")


# Gemini calls go through shared gemini_client.gemini_generate()


def _get_sentence_transformer():
    """Lazily load sentence-transformer for local embeddings."""
    global _sentence_transformer
    if _sentence_transformer is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[OK] Loaded sentence-transformers for local embeddings (384 dims)")
        except ImportError as e:
            logger.warning(f"sentence-transformers unavailable (import failed): {e}. "
                           "Install with: pip install sentence-transformers")
            _sentence_transformer = False
        except Exception as e:
            logger.warning(f"sentence-transformers failed to load the model: {e}")
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
    context_tokens: int = 0  # tokens of retrieved chunk context fed to the LLM
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

    def __init__(self, auto_build: bool = True):
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner product = cosine similarity
        self.chunks: list[str] = []
        self.chunk_metadata: list[dict] = []

        # Try to load pre-built FAISS index from disk
        # Use absolute path: work up from this file → backend → graphrag-hackathon → data
        faiss_path = Path(__file__).resolve().parent.parent.parent / "data" / "faiss_index.pkl"

        logger.info(f"Attempting to load FAISS index from: {faiss_path}")
        logger.info(f"Path exists: {faiss_path.exists()}")

        if faiss_path.exists() and RAG_USE_PREBUILT_INDEX:
            try:
                import pickle
                with open(faiss_path, "rb") as f:
                    data = pickle.load(f)
                    self.index = data["index"]
                    self.chunks = data["chunks"]
                    self.chunk_metadata = data.get("metadata", [])
                logger.info(f"[OK] Loaded FAISS index from {faiss_path} ({len(self.chunks)} chunks, {self.index.ntotal} vectors)")
            except Exception as e:
                logger.error(f"[ERR] Failed to load FAISS index: {e}", exc_info=True)
                # Fall through to build from the corpus
                if auto_build:
                    self._build_index_from_sample_docs()
        elif auto_build:
            logger.warning(f"[WARN]  FAISS index not found at {faiss_path}. Building from corpus...")
            self._build_index_from_sample_docs()

    def _build_index_from_sample_docs(self):
        """Dynamically build FAISS index from the corpus with token-aware chunking."""
        # Reuse the same robust, format-agnostic chunker used by the ingestion
        # pipeline so .txt papers (no markdown headers) chunk correctly.
        from ..graph.ingestion import chunk_text

        project_root = Path(__file__).resolve().parent.parent.parent
        sample_docs_dir = project_root / RAG_DATA_DIR

        if not sample_docs_dir.exists():
            logger.warning(f"Corpus directory not found at {sample_docs_dir}")
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

                if not content.strip():
                    continue

                # Token-aware chunking with overlap (works for .md and plain .txt)
                chunks = [c.strip() for c in chunk_text(content) if c.strip()]
                for chunk_idx, chunk in enumerate(chunks):
                    self.chunks.append(chunk)
                    self.chunk_metadata.append({
                        "source": doc_file.name,
                        "chunk": chunk_idx,
                    })
            except Exception as e:
                logger.warning(f"Failed to load {doc_file.name}: {e}")

        logger.info(f"[FILE] Chunked {len(doc_files)} documents into {len(self.chunks)} chunks")

        # Embed all chunks
        if self.chunks:
            try:
                logger.info(f"Embedding {len(self.chunks)} chunks...")
                embeddings = self._embed_batch(self.chunks)
                vectors = np.array(embeddings, dtype="float32")
                _assert_real_embeddings(vectors)
                faiss.normalize_L2(vectors)
                self.index.add(vectors)
                logger.info(f"[OK] Built FAISS index with {self.index.ntotal} vectors from {len(self.chunks)} chunks")
            except RuntimeError:
                raise  # zero-vector guard — abort loudly, do not swallow
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
        _assert_real_embeddings(vectors)
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
                logger.info(f"[OK] Retrieved {len(retrieved)} chunks from FAISS (ntotal: {self.index.ntotal})")
            except Exception as e:
                logger.error(f"FAISS search failed: {e}. Falling back to first chunks.")
                retrieved = self.chunks[:top_k]
        elif self.chunks:
            # Fallback: return first K chunks if embedding/search fails
            logger.warning(f"[WARN] Embedding or index unavailable. Using first {top_k} chunks as fallback.")
            retrieved = self.chunks[:top_k]
        else:
            retrieved = ["[No documents available. Please ingest documents first.]"]

        # 3. Build context (this is where tokens pile up)
        context = "\n\n---\n\n".join(retrieved)
        context_tokens = count_context_tokens(context)

        # 4. Build prompt
        system_prompt = (
            "You are an expert assistant. The context below was retrieved "
            "automatically and may be partially or entirely irrelevant. Use only "
            "the parts that directly address the question, and rely on your own "
            "expertise for the rest. Always give a complete, accurate answer — "
            "never refuse or say the context is insufficient. "
            + CONCISE_ANSWER_INSTRUCTION
        )
        user_prompt = f"""Question: {question}

Optional reference passages (retrieved automatically — use only if relevant, ignore if not):
{context}

Answer the question completely, using your own expertise plus any relevant passages above. Do not say the passages are insufficient — just answer the question:"""

        # 5. Call Gemini via shared client (accurate token counts)
        result = gemini_generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=MAX_OUTPUT_TOKENS,  # shared cap — equal across all 3 pipelines
        )

        latency_ms = (time.time() - t0) * 1000

        return RAGResult(
            answer=result["answer"],
            retrieved_chunks=retrieved,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            total_tokens=result["total_tokens"],
            latency_ms=latency_ms,
            context_tokens=context_tokens,
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
        # Use tiktoken locally (no API call needed)
        from ..llm.gemini_client import count_context_tokens
        return count_context_tokens(text)

    def get_index_stats(self) -> dict:
        return {
            "total_chunks": len(self.chunks),
            "index_size": self.index.ntotal,
            "embedding_dim": EMBEDDING_DIM,
        }
        