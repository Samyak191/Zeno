import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import os

embedder = SentenceTransformer("all-MiniLM-L6-v2")  # tiny, fast, free
client  = chromadb.PersistentClient(path="./chroma_db")

def get_collection(client_id: str):
    return client.get_or_create_collection(name=f"docs_{client_id}")

def ingest_pdf(filepath: str, client_id: str):
    reader = PdfReader(filepath)
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        # Split into ~300 char chunks with overlap
        words = text.split()
        for i in range(0, len(words), 60):
            chunk = " ".join(words[i:i+80])
            if chunk.strip():
                chunks.append(chunk)

    col = get_collection(client_id)
    embeddings = embedder.encode(chunks).tolist()
    ids = [f"{os.path.basename(filepath)}_chunk_{i}" for i in range(len(chunks))]

    col.upsert(documents=chunks, embeddings=embeddings, ids=ids)
    print(f"Ingested {len(chunks)} chunks from {filepath}")

def retrieve(query: str, client_id: str, top_k: int = 4):
    col = get_collection(client_id)
    if col.count() == 0:
        return ""
    q_embed = embedder.encode([query]).tolist()
    results = col.query(query_embeddings=q_embed, n_results=min(top_k, col.count()))
    return "\n\n".join(results["documents"][0])