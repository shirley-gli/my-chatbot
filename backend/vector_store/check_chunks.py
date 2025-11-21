from vector_db1 import get_chroma_collection

# Get Chroma collection
client, collection = get_chroma_collection()

# Query all documents (safe way)
try:
    results = collection.query(
        query_embeddings=[],   # empty to just fetch all stored docs
        n_results=10,          # number of top results per query
        include=["documents", "metadatas"]
    )
    
    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    print("📦 Documents in vector DB:")
    for i, docs in enumerate(documents):
        for j, doc in enumerate(docs):
            meta = metadatas[i][j] if metadatas else {}
            print(f"{i}-{j}: {doc[:100]}... (metadata: {meta})")

except Exception as e:
    print(f"❌ Error querying collection: {e}")
