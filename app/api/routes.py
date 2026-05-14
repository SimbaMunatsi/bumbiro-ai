import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_rag_pipeline, get_current_user
from app.api.schemas import QueryRequest, QueryResponse
from app.models.user import User
from app.core.database import get_db

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest, 
    rag=Depends(get_rag_pipeline),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # --- DIAGNOSTIC LOGGING ---
    try:
        print(f"\n--- DEBUG: Starting Retrieval for: {request.query} ---")
        v_results = rag.vector_retriever.invoke(request.query)
        b_results = rag.bm25_retriever.invoke(request.query)
        print(f"--- VECTOR FOUND {len(v_results)} CHUNKS ---")
        for doc in v_results: print(f"V-DOC: {doc.page_content[:100]}...")
        print(f"--- BM25 FOUND {len(b_results)} CHUNKS ---")
        for doc in b_results: print(f"B-DOC: {doc.page_content[:100]}...")
        print("--- DEBUG: Retrieval Check Complete ---\n")
    except Exception as e:
        print(f"--- DEBUG: Retrieval Check Failed: {e} ---")

    secure_session_id = f"user_{current_user.id}_{request.session_id}"
    result = await rag.run(query=request.query, session_id=secure_session_id, db=db)
    
    return {
        "answer": str(result.get("answer", "")),
        "sources": result.get("sources", [])
    }


async def simulated_stream(answer: str, sources: list):
    """
    Yields JSON chunks. It streams the text tokens first, 
    then sends the sources list in the final chunk.
    """
    for token in answer.split():
        # Re-add the space removed by split()
        chunk_data = {"type": "chunk", "content": token + " "}
        yield f"{json.dumps(chunk_data)}\n"
        await asyncio.sleep(0.02)  # Simulate streaming delay
    
    # Yield the sources at the very end
    sources_data = {"type": "sources", "content": sources}
    yield f"{json.dumps(sources_data)}\n"


@router.post("/query-stream")
async def query_stream(
    request: QueryRequest, 
    rag=Depends(get_rag_pipeline),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    secure_session_id = f"user_{current_user.id}_{request.session_id}"
    
    # Await the full generation
    result = await rag.run(
        query=request.query,
        session_id=secure_session_id,
        db=db
    )

    clean_sources = result.get("sources", [])
    answer_text = str(result.get("answer", ""))

    # Stream the resulting text and sources back using JSON Lines format
    return StreamingResponse(
        simulated_stream(answer_text, clean_sources),
        media_type="application/x-ndjson"
    )


@router.get("/health")
def health():
    return {"status": "ok", "message": "BumbiroAI API is running."}