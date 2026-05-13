import asyncio
from langchain_community.retrievers import BM25Retriever
from app.core.vector_store import get_vector_store
from app.retrieval.base_retriever import BaseRetriever

class HybridRetriever(BaseRetriever):
    def __init__(self, documents, k=8, rrf_k=60):
        self.vector_store = get_vector_store()
        self.keyword_retriever = BM25Retriever.from_documents(documents)
        self.keyword_retriever.k = k
        self.k = k
        self.rrf_k = rrf_k 

    async def retrieve(self, query):
        # This keeps FastAPI fully non-blocking without breaking SQLAlchemy!
        
        vector_results = await asyncio.to_thread(
            self.vector_store.similarity_search, query, k=self.k
        )
        
        keyword_results = await asyncio.to_thread(
            self.keyword_retriever.invoke, query
        )

        # Reciprocal Rank Fusion (Weighted Hybrid Search)
        doc_scores = {}
        content_to_doc = {}

        # Score Vector Results
        for rank, doc in enumerate(vector_results):
            content = doc.page_content
            content_to_doc[content] = doc
            doc_scores[content] = doc_scores.get(content, 0.0) + 1.0 / (self.rrf_k + rank)

        # Score BM25 Results
        for rank, doc in enumerate(keyword_results):
            content = doc.page_content
            content_to_doc[content] = doc
            doc_scores[content] = doc_scores.get(content, 0.0) + 1.0 / (self.rrf_k + rank)

        # Sort documents by their combined RRF score
        sorted_contents = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
        
        return [content_to_doc[content] for content in sorted_contents[:self.k]]