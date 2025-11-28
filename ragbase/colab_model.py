from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI
import os

from ragbase.config import Config


def create_llm() -> BaseLanguageModel:
    if Config.Model.USE_LOCAL:
        try:

            API = ""
            api_key = os.getenv("GOOGLE_API_KEY") or API
            
            return ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=api_key,
                temperature=Config.Model.TEMPERATURE,
                max_tokens=Config.Model.MAX_TOKENS,
            )
        except Exception as e:
            print(f"Error loading Gemini: {e}")
            from langchain_community.llms import FakeListLLM
            return FakeListLLM(responses=["I'm a placeholder LLM. Please configure Google API key."])
    else:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                temperature=Config.Model.TEMPERATURE,
                model_name=Config.Model.REMOTE_LLM,
                max_tokens=Config.Model.MAX_TOKENS,
            )
        except ImportError:
            print("Groq not available, using fallback")
            from langchain_community.llms import FakeListLLM
            return FakeListLLM(responses=["I'm a placeholder LLM. Groq not configured."])


def create_embeddings() -> FastEmbedEmbeddings:
    return FastEmbedEmbeddings(model_name=Config.Model.EMBEDDINGS)


def create_reranker():
    from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
    return FlashrankRerank(model=Config.Model.RERANKER)