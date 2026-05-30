import chromadb
from fastembed import TextEmbedding
from pypdf import PdfReader
import os

embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
client   = chromadb.PersistentClient(path="./chroma_db")

def get_collection(client_id: str):
    return client.get_or_create_collection(name=f"docs_{client_id}")

def ingest_pdf(filepath: str, client_id: str):
    reader = PdfReader(filepath)
    chunks = []
    for page in reader.pages:
        text = page.extract_text() or ""
        words = text.split()
        for i in range(0, len(words), 60):
            chunk = " ".join(words[i:i+80])
            if chunk.strip():
                chunks.append(chunk)

    col        = get_collection(client_id)
    embeddings = list(embedder.embed(chunks))
    embeddings = [e.tolist() for e in embeddings]
    ids        = [f"{os.path.basename(filepath)}_chunk_{i}" for i in range(len(chunks))]

    col.upsert(documents=chunks, embeddings=embeddings, ids=ids)
    print(f"Ingested {len(chunks)} chunks from {filepath}")

def retrieve(query: str, client_id: str, top_k: int = 4):
    col = get_collection(client_id)
    if col.count() == 0:
        return ""
    q_embed = list(embedder.embed([query]))[0].tolist()
    results = col.query(query_embeddings=[q_embed], n_results=min(top_k, col.count()))
    return "\n\n".join(results["documents"][0])