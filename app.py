import asyncio
import random
import tempfile
import os
import base64

import streamlit as st
from dotenv import load_dotenv

from ragbase.chain import ask_question, create_chain
from ragbase.config import Config
from ragbase.ingestor import Ingestor
from ragbase.model import create_llm
from ragbase.retriever import create_retriever
from ragbase.uploader import upload_files

from ragbase.scrapper import summarize_text_for_search, fetch_wikipedia_summary, clean_search_query,fetch_top_wikipedia_results
from langchain_core.documents import Document
from ragbase.pdf_maker import save_summary_as_pdf,save_wikipedia_results_to_pdf

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


@st.cache_resource
def build_qa_chain_from_text(user_input):
    if isinstance(user_input, str) and not user_input.lower().endswith(".pdf"):

        loaded_documents = [Document(page_content=user_input)]
    else:
        loaded_documents = Ingestor().ingest([user_input])

    ingestor = Ingestor()
    vector_store = ingestor.ingest_from_documents(loaded_documents) \
        if hasattr(ingestor, "ingest_from_documents") else None

    llm = create_llm()
    retriever = create_retriever(llm, vector_store=vector_store) if vector_store else create_retriever(llm)
    chain = create_chain(llm, retriever)
    return chain


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


def display_pdf_demo(pdf_path):
    try:
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        pdf_display = f'''
        <div style="border: 2px solid #e0e0e0; border-radius: 10px; padding: 10px; background-color: #f9f9f9;">
            <h4 style="margin-top: 0; color: #333;">📄 PDF Preview - First Page</h4>
            <iframe 
                src="data:application/pdf;base64,{base64_pdf}" 
                width="100%" 
                height="500" 
                style="border: 1px solid #ddd; border-radius: 5px;"
                type="application/pdf">
            </iframe>
            <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                <strong>File:</strong> {os.path.basename(pdf_path)} | 
                <strong>Size:</strong> {os.path.getsize(pdf_path) // 1024} KB
            </div>
        </div>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        with open(pdf_path, "rb") as file:
            st.download_button(
                label="📥 Download Full PDF",
                data=file,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Error displaying PDF demo: {e}")


def show_input_method():
    st.header("RagBase")
    st.subheader("Get answers from your documents or text")
    
    input_method = st.radio(
        "Choose input method:",
        ["Upload PDF", "Enter Text"],
        horizontal=True
    )
    
    if input_method == "Upload PDF":
        uploaded_file = st.file_uploader(
            label="Upload PDF file", 
            type=["pdf"], 
            accept_multiple_files=False,
            help="Upload a PDF document"
        )
        
        if not uploaded_file:
            st.warning("Please upload a PDF document to continue!")
            st.stop()

        uploaded_files = [uploaded_file]

        with st.spinner("Analyzing your document(s)..."):
            chain = build_qa_chain_from_pdf(uploaded_files)
            
            st.subheader("📚 Uploaded Documents Preview")
            for i, file in enumerate(uploaded_files):
                with st.expander(f"📄 Document {i+1}: {file.name}", expanded=(i==0)):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(file.getvalue())
                        tmp_path = tmp_file.name
                    
                    display_pdf_demo(tmp_path)
                    
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass

        return chain, "pdf"
    
    else:
        text_input = st.text_area(
            label="Enter your text",
            height=25,
            placeholder="Enter your word or paragraph here...",
            help="Enter the word or paragraph you want to research."
        )

        if not text_input.strip():
            st.warning("Please enter some text to continue!")
            st.stop()

        if len(text_input.strip()) < 5:
            st.warning("Please enter at least 5 characters of text.")
            st.stop()

        with st.spinner("Summarizing your text for Wikipedia search..."):
            llm = create_llm()
            summary_query = summarize_text_for_search(text_input, llm)
            query = clean_search_query(summary_query)
            st.info(f"🔍 Searching Wikipedia for: **{query}**")

            results = fetch_top_wikipedia_results(query, n=3, sentences=10)
            print(f"[Debug] Wikipedia results count: {len(results)}")

            if not results:
                st.warning(f"❌ No Wikipedia page found for your query: **{query}**")
                st.stop()

            disambig_results = [r for r in results if r.get("is_disambiguation", False)]
            if disambig_results:
                disambig_content = disambig_results[0]['content']
                options = [line.strip("• ").strip() for line in disambig_content.splitlines() if line.startswith("•")]
                
                st.warning("⚠️ Multiple possible topics found. Please select one:")
                selected_option = st.radio("Choose the specific topic to research:", options)

                confirm_clicked = st.button("✅ Confirm Selection", type="primary")

                if not confirm_clicked:
                    st.info("👆 Please confirm your selection to continue")
                    st.stop()
                
                st.success(f"✅ You selected: **{selected_option}**")

                with st.spinner(f"Searching for '{selected_option}'..."):
                    results = fetch_top_wikipedia_results(selected_option, n=1, sentences=10)
                    if not results:
                        st.warning(f"❌ No Wikipedia page found for your selected topic: **{selected_option}**")
                        st.stop()

        with st.spinner("Saving Wikipedia results as PDF..."):
            pdf_path = None
            if len(results) == 1:
                pdf_path = save_summary_as_pdf(
                    title=results[0]['title'],
                    content=results[0]['content'],
                    show_preview=False
                )
                st.success(f"📄 Wikipedia summary saved as PDF: `{pdf_path}`")

            else:
                pdf_path = save_wikipedia_results_to_pdf(
                    query, 
                    top_n=3, 
                    logo_path="images/logo.png",
                    show_preview=False
                )
                if pdf_path:
                    st.success(f"📄 Wikipedia results saved as PDF: `{pdf_path}`")
                else:
                    st.error("Failed to create PDF from Wikipedia results")
                    st.stop()

        if pdf_path and os.path.exists(pdf_path):
            st.subheader("📘 Wikipedia Summary Preview")
            display_pdf_demo(pdf_path)
        else:
            st.warning("⚠️ No PDF available to display.")

        return None, "text"


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

        st.info("⚠️ Text input mode is read-only. Chat with the model is disabled in this mode.")
        return 
    
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