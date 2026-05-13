class IngestionPipeline:
    def __init__(
        self,
        loader,
        cleaner,
        chunker,
        enricher,
        vector_store
    ):
        self.loader = loader
        self.cleaner = cleaner
        self.chunker = chunker
        self.enricher = enricher
        self.vector_store = vector_store

    def run(self):
        print("Loading documents...")
        documents = self.loader.load()
        
        print("Cleaning documents...")
        cleaned_docs = self.cleaner.clean(documents)
        
        print("Chunking documents...")
        chunks = self.chunker.chunk(cleaned_docs)
        
        print("Enriching metadata and generating deterministic IDs...")
        enriched_chunks = self.enricher.enrich(chunks)
        
        print("Storing chunks in vector database...")
        # batch_size can be adjusted depending on API limits
        total_stored = self.vector_store.store(enriched_chunks, batch_size=100)
        
        return total_stored