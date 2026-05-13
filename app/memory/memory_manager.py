import asyncio
from sqlalchemy.orm import Session
from app.memory.conversation_memory import ConversationMemory
from app.memory.agentic_memory import AgenticMemory

class MemoryManager:
    def __init__(self, db: Session, session_id: str):
        self.session_id = session_id
        self.conversation = ConversationMemory(db, session_id)
        self.agentic = AgenticMemory(session_id)

    async def build_context(self, query: str) -> dict:
        # Fetch short term memory from Postgres
        conversation_context = self.conversation.get_context()
        
        # Fetch long term, decayed memory from pgvector
        semantic_context = await self.agentic.retrieve_relevant_facts(query)

        return {
            "conversation": conversation_context,
            "semantic": semantic_context
        }

    def update_sync(self, query: str, answer: str):
        # 1. Save standard conversation synchronously to Postgres
        self.conversation.add("user", query)
        self.conversation.add("assistant", answer)

    async def update_async(self, query: str, answer: str):
        # 2. Trigger the LLM Reflection process asynchronously 
        await self.agentic.reflect_and_store(query, answer)

def get_memory_manager(db: Session, session_id: str) -> MemoryManager:
    return MemoryManager(db, session_id)