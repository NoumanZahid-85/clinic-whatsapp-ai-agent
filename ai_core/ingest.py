import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from ai_core.rag import ingest_knowledge_base

if __name__ == "__main__":
    print("Ingesting knowledge base into ChromaDB...")
    ingest_knowledge_base()
    print("Done!")
