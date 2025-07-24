import os 
import uuid
import gc 
import tempfile
import streamlit as st 



from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI


from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.core import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.readers.docling import DoclingReader
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

import torch



def reset_chat():
    st.session_state.messages = []
    st.session_state.context = None
    gc.collect()

if "id" not in st.session_state:
    st.session_state.id = uuid.uuid4()
    st.session_state.file_cache = {}

session_id = st.session_state.id



load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
ollama_url = os.environ.get("OLLAMA", "http://ollama:11434")


@st.cache_resource


def load_local_llm():
    llm = Ollama(model="mistral:7b", base_url=ollama_url, request_timeout=200)
    return llm


def load_openai_llm():
    llm = OpenAI(model="gpt-4o", request_timeout=200, api_key=openai_api_key)
    return llm



with st.sidebar:

    st.header("RAG Mode Selection")
    mode = st.radio("Choose LLM mode:", ["Local (Ollama)", "OpenAI API"])

    st.header("Upload Document")

    uploaded_file = st.file_uploader("Upload your file", type=["docx", "xlsx", "pdf"])
    if uploaded_file:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                file_key = f"{session_id}-{uploaded_file.name}"
                st.write("Indexing your document...")

                # Ajout de la barre de progression
                progress_bar = st.progress(0, text="Lecture du document...")

                if file_key not in st.session_state.get('file_cache', {}):
                    progress_bar.progress(10, text="Parsing du document...")

                    if os.path.exists(temp_dir):
                        reader = DoclingReader()
                        loader = SimpleDirectoryReader(
                            input_dir=temp_dir,
                            file_extractor={".docx": reader,
                                            ".xlsx": reader, 
                                            ".pdf": reader}
                        )
                    else:    
                        st.error('Could not find the file you uploaded, please check again...')
                        st.stop()
                    
                    docs = loader.load_data()
                    progress_bar.progress(30, text="Indexation des chunks...")

                    if mode == "Local (Ollama)":
                        # setup llm & embedding model
                        llm= load_local_llm()
                        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en-v1.5", trust_remote_code=True, device="cpu")
                        Settings.embed_model = embed_model
                        node_parser = MarkdownNodeParser(chunk_size=512)

                        chroma_host = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
                        chroma_client = chromadb.HttpClient(host=chroma_host)
                        collection = chroma_client.get_or_create_collection(name="docxrag")
                        vector_store = ChromaVectorStore(chroma_collection=collection)

                        index = VectorStoreIndex.from_documents(
                            documents=docs,
                            vector_store=vector_store,
                            transformations=[node_parser],
                            show_progress=True
                        )
                        progress_bar.progress(70, text="Création du moteur de requête...")

                        Settings.llm = llm
                        query_engine = index.as_query_engine(streaming=True,retriever_mode="default")

                        qa_prompt_tmpl_str = (
                        "Context information is below.\n"
                        "---------------------\n"
                        "{context_str}\n"
                        "---------------------\n"
                        "En te basant uniquement sur le contexte ci-dessus, réponds à la question en FRANÇAIS, de façon précise et concise. Si tu ne sais pas, dis simplement 'Je ne sais pas !'.\n"
                        "Query: {query_str}\n"
                        "Réponse : "
                        )
                        qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)

                        query_engine.update_prompts(
                            {"response_synthesizer:text_qa_template": qa_prompt_tmpl}
                        )
                        
                        st.session_state.file_cache[file_key] = query_engine
                        progress_bar.progress(100, text="Indexation terminée !")
                        st.success("Ready to Chat!")  # <-- Ajout ici

                    else:
                        llm = load_openai_llm()
                        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en-v1.5", trust_remote_code=True)
                        Settings.embed_model = embed_model
                        node_parser = MarkdownNodeParser(chunk_size=2048)
                        chroma_host = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
                        chroma_client = chromadb.HttpClient(host=chroma_host)
                        collection = chroma_client.get_or_create_collection(name="docxrag")
                        vector_store = ChromaVectorStore(chroma_collection=collection)

                        index = VectorStoreIndex.from_documents(
                            documents=docs,
                            vector_store=vector_store,
                            transformations=[node_parser],
                            show_progress=True
                        )
                        progress_bar.progress(70, text="Création du moteur de requête...")

                        Settings.llm = llm
                        query_engine = index.as_query_engine(streaming=True, retriever_mode="default")

                        qa_prompt_tmpl_str = (
                        "Context information is below.\n"
                        "---------------------\n"
                        "{context_str}\n"
                        "---------------------\n"
                        "En te basant uniquement sur le contexte ci-dessus, réponds à la question en FRANÇAIS, de façon précise et concise. Si tu ne sais pas, dis simplement 'Je ne sais pas !'.\n"
                        "Query: {query_str}\n"
                        "Réponse : "
                        )
                        qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)

                        query_engine.update_prompts(
                            {"response_synthesizer:text_qa_template": qa_prompt_tmpl}
                        )
                        
                        st.session_state.file_cache[file_key] = query_engine
                        progress_bar.progress(100, text="Indexation terminée !")
                        st.success("Ready to Chat!")  # <-- Ajout ici

                else:
                    query_engine = st.session_state.file_cache[file_key]
                    st.success("Ready to Chat!")

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.stop()




col1, col2 = st.columns([6, 1])

with col1:
    st.header(f"RAG local ou Openai")

with col2:
    st.button("Clear ↺", on_click=reset_chat)

# Initialize chat history
if "messages" not in st.session_state:
    reset_chat()


# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Accept user input
if prompt := st.chat_input("What's up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Simulate stream of response with milliseconds delay
        streaming_response = query_engine.query(prompt)
        
        for chunk in streaming_response.response_gen:
            full_response += chunk
            message_placeholder.markdown(full_response + "▌")

        # full_response = query_engine.query(prompt)

        message_placeholder.markdown(full_response)
        # st.session_state.context = ctx

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})


# Clear file_cache if mode changes JE SAIS PAS ENCORE COMMENT CA MARCHE
if "last_mode" not in st.session_state or st.session_state.last_mode != mode:
    st.session_state.file_cache = {}
    st.session_state.last_mode = mode
