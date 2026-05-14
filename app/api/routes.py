import asyncio
import json
import re
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
    secure_session_id = f"user_{current_user.id}_{request.session_id}"
    result = await rag.run(query=request.query, session_id=secure_session_id, db=db)
    
    return {
        "answer": str(result.get("answer", "")),
        "sources": result.get("sources", [])
    }


async def simulated_stream(answer: str, sources: list):
    """
    Yields JSON chunks. Preserves all whitespace and newlines 
    to maintain Markdown formatting.
    """
    # re.split(r'(\s+)') splits the string but KEEPS the separators (newlines, spaces)
    tokens = re.split(r'(\s+)', answer)
    
    for token in tokens:
        if not token:
            continue
        chunk_data = {"type": "chunk", "content": token}
        yield f"{json.dumps(chunk_data)}\n"
        # Small delay for visual effect
        await asyncio.sleep(0.01)
    
    # Final chunk for sources
    yield f"{json.dumps({'type': 'sources', 'content': sources})}\n"


@router.post("/query-stream")
async def query_stream(
    request: QueryRequest, 
    rag=Depends(get_rag_pipeline),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # This diagnostic print helps you see the 502 timing in Render logs
    print(f"--- Processing stream request for user: {current_user.email} ---")
    
    secure_session_id = f"user_{current_user.id}_{request.session_id}"
    
    # The heavy lifting happens here (Retrieval + LLM)
    result = await rag.run(
        query=request.query,
        session_id=secure_session_id,
        db=db
    )

    clean_sources = result.get("sources", [])
    answer_text = str(result.get("answer", ""))

    return StreamingResponse(
        simulated_stream(answer_text, clean_sources),
        media_type="application/x-ndjson"
    )


@router.get("/health")
def health():
    return {"status": "ok", "message": "BumbiroAI API is running."}