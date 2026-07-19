import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader

CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
KNOWLEDGE_BASE_DIR = os.path.join(
    os.path.dirname(__file__), "knowledge_base"
)


def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def get_vector_store():
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings,
    )


def ingest_knowledge_base():
    loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)

    embeddings = get_embeddings()
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
    )
    print(f"Ingested {len(chunks)} chunks into ChromaDB at {CHROMA_PATH}")
    return vector_store


def search_knowledge_base(query: str, k: int = 3) -> list[str]:
    try:
        vector_store = get_vector_store()
        results = vector_store.similarity_search(query, k=k)
        return [doc.page_content for doc in results]
    except Exception as e:
        print(f"RAG search error: {e}")
        return []


if __name__ == "__main__":
    ingest_knowledge_base()
