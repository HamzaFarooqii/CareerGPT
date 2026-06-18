# ============================================================
# Vector Store — Numpy-Based Similarity Search
# ============================================================
# Instead of ChromaDB (which needs C++ build tools), we use
# a pure-Python solution with numpy. For our scale (< 10K jobs),
# this is fast enough and has ZERO extra dependencies.
#
# HOW IT WORKS:
# ─────────────
# 1. We load all job embeddings from MongoDB into memory
# 2. Stack them into a numpy matrix (N x 768)
# 3. To search: compute cosine similarity against ALL vectors
# 4. Return the top-K most similar
#
# With 10,000 jobs × 768 dimensions, the search takes < 50ms.
# That's fast enough for real-time use.
#
# CONCEPT: Why This Works at Our Scale
# ─────────────────────────────────────
# ChromaDB uses HNSW indexing for millions of vectors.
# We have hundreds. Brute-force numpy is simpler and just as fast.
# 
# If you scale to 100K+ jobs, THEN you'd switch to ChromaDB/Pinecone.
# But for a portfolio project, numpy is the smart choice.
# ============================================================

import numpy as np
from typing import Optional


class VectorStore:
    """
    In-memory vector store backed by numpy arrays.
    
    Stores vectors in RAM for fast similarity search.
    Data is loaded from MongoDB at startup and stays in sync.
    """

    def __init__(self):
        # Jobs: id → embedding mapping
        self._job_ids: list[str] = []
        self._job_embeddings: Optional[np.ndarray] = None  # shape: (N, 768)
        self._job_metadata: dict[str, dict] = {}  # id → {title, company, source}

        # Resumes: id → embedding mapping
        self._resume_ids: list[str] = []
        self._resume_embeddings: Optional[np.ndarray] = None
        self._resume_metadata: dict[str, dict] = {}

        print("🗄️  Vector store initialized (numpy-based, in-memory)")

    def add_job(self, job_id: str, embedding: list[float],
                title: str = "", company: str = "", source: str = "",
                document: str = ""):
        """Add or update a job embedding."""
        if job_id in self._job_metadata:
            # Update existing — find index and replace
            idx = self._job_ids.index(job_id)
            if self._job_embeddings is not None:
                self._job_embeddings[idx] = np.array(embedding)
        else:
            # Add new
            self._job_ids.append(job_id)
            vec = np.array(embedding).reshape(1, -1)
            if self._job_embeddings is None:
                self._job_embeddings = vec
            else:
                self._job_embeddings = np.vstack([self._job_embeddings, vec])

        self._job_metadata[job_id] = {
            "title": title, "company": company, "source": source
        }

    def add_resume(self, resume_id: str, embedding: list[float],
                   title: str = "", document: str = ""):
        """Add or update a resume embedding."""
        if resume_id in self._resume_metadata:
            idx = self._resume_ids.index(resume_id)
            if self._resume_embeddings is not None:
                self._resume_embeddings[idx] = np.array(embedding)
        else:
            self._resume_ids.append(resume_id)
            vec = np.array(embedding).reshape(1, -1)
            if self._resume_embeddings is None:
                self._resume_embeddings = vec
            else:
                self._resume_embeddings = np.vstack([self._resume_embeddings, vec])

        self._resume_metadata[resume_id] = {"title": title}

    def find_similar_jobs(self, query_embedding: list[float], top_k: int = 20) -> dict:
        """
        Find the top-K most similar jobs using cosine similarity.
        
        CONCEPT: Brute-Force Cosine Search
        ───────────────────────────────────
        1. Normalize the query vector (make it unit length)
        2. Normalize all job vectors (make them unit length)
        3. Dot product of query with all jobs = cosine similarities
        4. Sort by similarity, take top K
        
        With numpy, step 3 is a single matrix multiplication:
          similarities = query_normalized @ jobs_normalized.T
        
        This computes ALL similarities at once — numpy does this
        in optimized C under the hood, so it's very fast.
        
        Returns dict matching ChromaDB's format for compatibility:
          {"ids": [[...]], "distances": [[...]], "metadatas": [[...]]}
        
        Note: We return DISTANCES (1 - similarity) not similarities,
        so the matching service code stays the same regardless of backend.
        """
        if self._job_embeddings is None or len(self._job_ids) == 0:
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}

        query = np.array(query_embedding).reshape(1, -1)

        # Normalize vectors for cosine similarity
        query_norm = query / (np.linalg.norm(query, axis=1, keepdims=True) + 1e-10)
        jobs_norm = self._job_embeddings / (
            np.linalg.norm(self._job_embeddings, axis=1, keepdims=True) + 1e-10
        )

        # Cosine similarities: (1, N) = (1, 768) @ (768, N)
        similarities = (query_norm @ jobs_norm.T).flatten()

        # Get top K indices (sorted by highest similarity)
        actual_k = min(top_k, len(self._job_ids))
        top_indices = np.argsort(similarities)[::-1][:actual_k]

        # Build results
        result_ids = [self._job_ids[i] for i in top_indices]
        result_distances = [float(1 - similarities[i]) for i in top_indices]  # Convert to distance
        result_metadatas = [self._job_metadata.get(self._job_ids[i], {}) for i in top_indices]

        return {
            "ids": [result_ids],
            "distances": [result_distances],
            "metadatas": [result_metadatas],
        }

    def get_stats(self) -> dict:
        """Get counts of vectors in the store."""
        return {
            "jobs_in_vector_store": len(self._job_ids),
            "resumes_in_vector_store": len(self._resume_ids),
        }


# Singleton instance
vector_store = VectorStore()
