import os
import json
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

KNOWLEDGE_BASE_DIR = Path("../knowledge_base")
CHROMA_DIR = Path("../chroma_db")

# Embedding model - free, runs locally
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def load_knowledge_base():
    """Load all .md files from knowledge_base folder"""
    docs = []
    for md_file in KNOWLEDGE_BASE_DIR.glob("*.md"):
        loader = TextLoader(str(md_file), encoding="utf-8")
        loaded = loader.load()
        for doc in loaded:
            doc.metadata["source"] = md_file.name
        docs.extend(loaded)
    print(f"Loaded {len(docs)} documents")
    return docs

def create_vector_store():
    """Chunk documents and store in ChromaDB"""
    docs = load_knowledge_base()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR)
    )
    print("Vector store created and saved!")
    return vectorstore

def get_vector_store():
    """Load existing vector store"""
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings
    )

def search_knowledge_base(query: str, k: int = 3):
    """Search knowledge base - returns top k chunks with scores"""
    vectorstore = get_vector_store()
    results = vectorstore.similarity_search_with_score(query, k=k)
    
    output = []
    for doc, score in results:
        output.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "similarity_score": round(1 - score, 3)
        })
    return output

if __name__ == "__main__":
    print("Building knowledge base...")
    create_vector_store()
    print("Done!")
    
    # Test search
    results = search_knowledge_base("refund policy")
    print("\nTest search - 'refund policy':")
    for r in results:
        print(f"  [{r['source']}] score={r['similarity_score']}")
        print(f"  {r['content'][:100]}...")