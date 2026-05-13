from app.core.vector_store import get_vector_store

class VectorStoreManager:
    def __init__(self, embeddings):
        self.vector_store = get_vector_store(embeddings=embeddings)

    def store(self, chunks, batch_size=100):
        if not chunks:
            return 0
            
        # Deduplicate chunks in-memory before database insertion ---
        unique_chunks = []
        seen_ids = set()
        duplicate_count = 0
        
        for chunk in chunks:
            chunk_id = chunk.metadata["chunk_id"]
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)
            else:
                duplicate_count += 1
                
        if duplicate_count > 0:
            print(f"Filtered out {duplicate_count} identical chunks before database insertion.")

        total_stored = 0
        
        # Batch processing to prevent timeouts/memory spikes
        for i in range(0, len(unique_chunks), batch_size):
            batch = unique_chunks[i:i + batch_size]
            
            # Extract our deterministic IDs for the upsert
            batch_ids = [chunk.metadata["chunk_id"] for chunk in batch]
            
            # Add to PGVector (upserting safely)
            self.vector_store.add_documents(documents=batch, ids=batch_ids)
            total_stored += len(batch)
            print(f"Stored batch of {len(batch)} chunks... ({total_stored}/{len(unique_chunks)})")
            
        return total_stored