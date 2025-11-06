import asyncio
import random
import tempfile
import os

import streamlit as st
from dotenv import load_dotenv

from ragbase.chain import ask_question, create_chain
from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.model import create_llm
from ragbase.retriever import create_retriever
from ragbase.uploader import upload_files

load_dotenv()

LOADING_MESSAGES = [
    "Calculating your answer through multiverse...",
    "Adjusting quantum entanglement...",
    "Summoning star wisdom... almost there!",
    "Consulting Schrödinger's cat...",
    "Warping spacetime for your response...",
    "Balancing neutron star equations...",
    "Analyzing dark matter... please wait...",
    "Engaging hyperdrive... en route!",
    "Gathering photons from a galaxy...",
    "Beaming data from Andromeda... stand by!",
]


@st.cache_resource(show_spinner=False)
def build_qa_chain_from_pdf(files):
    file_paths = upload_files(files)
    vector_store = Ingestor().ingest(file_paths)
    llm = create_llm()
    retriever = create_retriever(llm, vector_store=vector_store)
    return create_chain(llm, retriever)


@st.cache_resource(show_spinner=False)
def build_qa_chain_from_text(text):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(text)
        temp_file_path = f.name
    
    vector_store = Ingestor().ingest([temp_file_path])
    llm = create_llm()
    retriever = create_retriever(llm, vector_store=vector_store)
    
    os.unlink(temp_file_path)
    
    return create_chain(llm, retriever)


async def ask_chain(question: str, chain):
    full_response = ""
    assistant = st.chat_message(
        "assistant", avatar=str(Config.Path.IMAGES_DIR / "assistant-avatar.png")
    )
    with assistant:
        message_placeholder = st.empty()
        message_placeholder.status(random.choice(LOADING_MESSAGES), state="running")
        documents = []
        async for event in ask_question(chain, question, session_id="session-id-42"):
            if type(event) is str:
                full_response += event
                message_placeholder.markdown(full_response)
            if type(event) is list:
                documents.extend(event)
        for i, doc in enumerate(documents):
            with st.expander(f"Source #{i+1}"):
                st.write(doc.page_content)

    st.session_state.messages.append({"role": "assistant", "content": full_response})


def show_input_method():
    st.header("RagBase")
    st.subheader("Get answers from your documents or text")
    
    input_method = st.radio(
        "Choose input method:",
        ["Upload PDF", "Enter Text"],
        horizontal=True
    )
    
    if input_method == "Upload PDF":
        uploaded_files = st.file_uploader(
            label="Upload PDF files", 
            type=["pdf"], 
            accept_multiple_files=True,
            help="Upload one or more PDF documents"
        )
        if not uploaded_files:
            st.warning("Please upload PDF documents to continue!")
            st.stop()
        
        with st.spinner("Analyzing your document(s)..."):
            return build_qa_chain_from_pdf(uploaded_files), "pdf"
    
    else:
        text_input = st.text_area(
            label="Enter your text",
            height=25,
            placeholder="enter your text here...",
            help="Enter the word you want to know about. This is useful for future web scraping integration."
        )
        
        if not text_input:
            st.warning("Please enter some text to continue!")
            st.stop()
        
        if len(text_input.strip()) < 50:
            st.warning("Please enter at least 50 characters of text for better results.")
            st.stop()
        
        with st.spinner("Processing your text..."):
            return build_qa_chain_from_text(text_input), "text"


def show_message_history():
    for message in st.session_state.messages:
        role = message["role"]
        avatar_path = (
            Config.Path.IMAGES_DIR / "assistant-avatar.png"
            if role == "assistant"
            else Config.Path.IMAGES_DIR / "user-avatar.png"
        )
        with st.chat_message(role, avatar=str(avatar_path)):
            st.markdown(message["content"])


def show_chat_input(chain):
    if prompt := st.chat_input("Ask your question here"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message(
            "user",
            avatar=str(Config.Path.IMAGES_DIR / "user-avatar.png"),
        ):
            st.markdown(prompt)
        asyncio.run(ask_chain(prompt, chain))


def main():
    st.set_page_config(page_title="RagBase", page_icon="🐧")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi! I can help you get answers from your documents or text. Please upload a PDF or enter some text to get started!",
            }
        ]

    chain, input_type = show_input_method()
    
    if input_type == "pdf":
        st.success("✓ PDF documents processed successfully!")
    else:
        st.success("✓ Text content processed successfully!")
    
    if Config.CONVERSATION_MESSAGES_LIMIT > 0 and Config.CONVERSATION_MESSAGES_LIMIT <= len(
        st.session_state.messages
    ):
        st.warning(
            "You have reached the conversation limit. Refresh the page to start a new conversation."
        )
        st.stop()

    show_message_history()
    show_chat_input(chain)


if __name__ == "__main__":
    main()