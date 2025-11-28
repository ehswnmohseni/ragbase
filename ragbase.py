import os
import shutil
from pathlib import Path
from ragbase.config import Config
from ragbase.chain import ask_question, create_chain
from ragbase.ingestor import Ingestor
from ragbase.model import create_llm
from ragbase.retriever import create_retriever
from langchain_core.documents import Document
import asyncio

def process_pdf(pdf_path: str):

    if not pdf_path or not isinstance(pdf_path, str):
        raise ValueError("PDF path must be a non-empty string")
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError("File must be a PDF document")
    
    shutil.rmtree(Config.Path.DATABASE_DIR, ignore_errors=True)
    
    file_paths = [Path(pdf_path)]
    vector_store = Ingestor().ingest(file_paths)
    llm = create_llm()
    retriever = create_retriever(llm, vector_store=vector_store)
    chain = create_chain(llm, retriever)
    
    return chain

def process_question(question: str, chain):
    if not question or not isinstance(question, str):
        raise ValueError("Question must be a non-empty string")
    
    if len(question.strip()) < 2:
        raise ValueError("Question must be at least 2 characters long")
    
    async def ask_question_async():
        full_response = ""
        documents = []
        
        async for event in ask_question(chain, question, session_id="session-id-42"):
            if isinstance(event, str):
                full_response += event
            elif isinstance(event, list):
                documents.extend(event)
        
        return full_response, documents
    
    response, sources = asyncio.run(ask_question_async())
    
    return {
        "answer": response,
        "sources": sources
    }

def create_rag_system():
    class SimpleRAG:
        def __init__(self):
            self.chain = None
            self.is_loaded = False
        
        def load_pdf(self, pdf_path: str):
            self.chain = process_pdf(pdf_path)
            self.is_loaded = True
            return True
        
        def ask_question(self, question: str):
            if not self.is_loaded or not self.chain:
                raise ValueError("Please load a PDF first using load_pdf()")
            
            return process_question(question, self.chain)
    
    return SimpleRAG()


async def example_usage():
    try:
        chain = process_pdf("documents/AEG_BII.pdf")
        print("✅ PDF loaded successfully!")
        result = process_question("خلاصه این سند چیست؟", chain)
        print("🤖 پاسخ:", result["answer"])
        print("📚 منابع:", len(result["sources"]))
    except Exception as e:
        print(f"❌ خطا: {e}")
    rag = create_rag_system()
    try:
        rag.load_pdf("documents/AEG_BII.pdf")
        print("✅ PDF loaded successfully!")
        questions = [
            "موضوع اصلی این سند چیست؟",
            "چه نکات کلیدی مطرح شده است؟",
            "نتیجه‌گیری چیست؟"
        ]
        for q in questions:
            result = rag.ask_question(q)
            print(f"\n❓ سوال: {q}")
            print(f"🤖 پاسخ: {result['answer']}")
            print(f"📚 تعداد منابع: {len(result['sources'])}")
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    asyncio.run(example_usage())