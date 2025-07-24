"""
Script Streamlit pour un système de RAG local sur des fichiers .docx :

1. Initialisation de la session utilisateur :
   - Génère un UUID pour chaque session et stocke un cache de query_engines.
   - Charge le LLM Mistral-7B via Ollama (avec cache pour optimiser les appels).

2. Téléversement et indexation du document :
   - Lecture du .docx avec DoclingReader et découpage en nœuds Markdown (chunk_size, chunk_overlap).
   - Calcul des embeddings BGE via HuggingFaceEmbedding.
   - Stockage des vecteurs dans ChromaDB (ChromaVectorStore).   

3. Création du moteur de requête (query_engine) :
   - Paramètres ajustables :
     • chunk_size (taille max des fragments, ex. 512 ou 1024 tokens)
     • chunk_overlap (recouvrement entre fragments, ex. 0–100 tokens)
     • similarity_top_k (nombre de fragments renvoyés au LLM, ex. 5–20)
     • fetch_k (nombre de fragments examinés avant reranking, ex. 20)
   - Configuration du prompt template pour répondre en français.
   - https://docs.llamaindex.ai/en/stable/understanding/querying/querying/

4. Interface de chat :
   - Envoi du prompt utilisateur, récupération des k fragments les plus pertinents via recherche vectorielle.
   - Streaming de la réponse du LLM et affichage interactif.

"""



import os

import gc
import tempfile
import uuid
import pandas as pd

from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.core import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.readers.docling import DoclingReader
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

import streamlit as st


if "id" not in st.session_state:
    st.session_state.id = uuid.uuid4()
    st.session_state.file_cache = {}

session_id = st.session_state.id
client = None
ollama_url = os.environ.get("OLLAMA", "http://ollama:11434")


@st.cache_resource 

def load_llm():
    llm = Ollama(model="mistral:7b", base_url=ollama_url, request_timeout=200)
    return llm

def reset_chat():
    st.session_state.messages = []
    st.session_state.context = None
    gc.collect()


def display_excel(file):
    st.markdown("### Excel Preview")
    # Read the Excel file
    df = pd.read_excel(file)
    # Display the dataframe
    st.dataframe(df)


with st.sidebar:
    st.header(f"Add your documents!")
    
    uploaded_file = st.file_uploader("Choose your `.docx` file", type=["docx"])

    if uploaded_file:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                file_key = f"{session_id}-{uploaded_file.name}"
                st.write("Indexing your document...")

                if file_key not in st.session_state.get('file_cache', {}):

                    if os.path.exists(temp_dir):
                            reader = DoclingReader()
                            loader = SimpleDirectoryReader(
                                input_dir=temp_dir,
                                file_extractor={".docx": reader},
                            )
                    else:    
                        st.error('Could not find the file you uploaded, please check again...')
                        st.stop()
                    
                    docs = loader.load_data()

                    # setup llm & embedding model
                    llm=load_llm()
                    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en-v1.5", trust_remote_code=True)
                    # embed_model = HuggingFaceEmbedding(model_name="camembert/camembert-base-wikipedia-4gb", trust_remote_code=True)
                    Settings.embed_model = embed_model
                    node_parser = MarkdownNodeParser(chunk_size=512)  # taille des chunks et recouvrement

                    # Connexion à ChromaDB (service Docker) 
                    chroma_host = os.environ.get("CHROMA_HOST", "http://chromadb:8000")
                    chroma_client = chromadb.HttpClient(host=chroma_host)
                    collection = chroma_client.get_or_create_collection(name="docxrag")
                    vector_store = ChromaVectorStore(chroma_collection=collection)

                    # Indexation avec LlamaIndex et Chroma comme backend
                    index = VectorStoreIndex.from_documents(
                        documents=docs,
                        vector_store=vector_store,
                        transformations=[node_parser],
                        show_progress=True
                    )

                    # Create the query engine, where we use a cohere reranker on the fetched nodes
                    Settings.llm = llm
                    query_engine = index.as_query_engine(streaming=True,retriever_mode="default") # on peut preciser ici le top_k des chunks à renvoyer au LLM

                    # ====== Customise prompt template ======
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
                else:
                    query_engine = st.session_state.file_cache[file_key]

                # Inform the user that the file is processed and Display the PDF uploaded
                st.success("Ready to Chat!")
                # display_excel(uploaded_file)
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.stop()     

col1, col2 = st.columns([6, 1])

with col1:
    st.header(f"RAG pour des docx en utilisant Dockling & mistral-7b")

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