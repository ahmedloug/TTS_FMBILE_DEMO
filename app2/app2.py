import os 
import uuid
import gc 
import tempfile
import streamlit as st 
from pathlib import Path
import re
import hashlib

from dotenv import load_dotenv
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings, Document
from llama_index.llms.ollama import Ollama
from llama_index.core import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.readers.docling import DoclingReader
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

load_dotenv()


RAG_PROMPT = """
Vous êtes un assistant polyvalent :
- Capable de répondre à des questions factuelles à partir du contexte fourni.
- Capable de générer ou d’étendre des sections de test si l’utilisateur le demande.

Contexte disponible :
{context_str}

Instructions :
1. **Répondez d’abord** directement à la question posée, en utilisant *uniquement* le contexte donné.
2. Si la question inclut une demande de « générer », « étendre » ou « créer » des sections de test :
   - Inspirez‑vous du format et du style existants.
   - Si le contexte manque, inférez des détails cohérents en vous basant sur l’architecture et les exigences.
   - Pour chaque nouvelle section :
     - Utilisez un titre clair (niveau Markdown `##`).
     - Ajoutez une courte description.
     - Proposez 3–5 points d’actions ou critères de validation.
   - Respectez toujours le template de cas de test suivant :
     ```
     ## Titre du test
     Brève description de l'objectif du test.

     ### 1. Objectif
     Une phrase expliquant la finalité du test.

     ### 2. Prérequis
     - Condition matérielle ou logicielle nécessaire.
     - Configuration initiale.

     ### 3. Données d’entrée
     - Paramètre A : valeur / plage.
     - Paramètre B : valeur / plage.

     ### 4. Étapes de test
     1. Étape 1 : description détaillée.
     2. Étape 2 : description détaillée.
     3. Étape 3 : description détaillée.

     ### 5. Résultats attendus
     - Étape 1 : résultat mesurable ou observable.
     - Étape 2 : résultat mesurable ou observable.

     ### 6. Critères de réussite / échec
     - Condition de succès.
     - Condition d’échec.

     ### 7. Références
     - Exigence(s) associée(s) (ex : REQ‑TS‑001).
     - Section(s) du document.
     ```
3. Si la question est purement factuelle, fournissez une réponse précise et structurée (puces, exemples chiffrés, renvois aux sections si besoin).
4. Ne mentionnez jamais les instructions internes dans votre réponse finale.

Question :
{query_str}

Réponse :
"""


DATA_DIR = "data"

def reset_chat():
    st.session_state.messages = []
    st.session_state.context = None
    st.session_state.selected_sections_final = []
    gc.collect()

def init_session_state():
    if "id" not in st.session_state:
        st.session_state.id = uuid.uuid4()
        st.session_state.file_cache = {}
        st.session_state.selected_sections_final = []

init_session_state()
session_id = st.session_state.id

@st.cache_resource
def load_local_llm():
    ollama_url = os.environ.get("OLLAMA", "http://ollama:11434")
    return Ollama(model="mistral:7b", base_url=ollama_url, request_timeout=200)

@st.cache_resource
def load_openai_llm():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(model="gpt-4", request_timeout=200, api_key=openai_api_key)

@st.cache_resource
def get_embed_model():
    return HuggingFaceEmbedding(model_name="BAAI/bge-large-en-v1.5", trust_remote_code=True, device="cpu")

def get_document_fingerprint(selected_files):
    """Créer une empreinte unique basée sur les fichiers sélectionnés"""
    file_signatures = []
    
    for fname in sorted(selected_files):
        fpath = Path(DATA_DIR) / fname
        if fpath.exists():
            stat = fpath.stat()
            # Signature = nom + taille + date modification
            signature = f"{fname}:{stat.st_size}:{int(stat.st_mtime)}"
            file_signatures.append(signature)
    
    # Hash MD5 de toutes les signatures
    content = "|".join(file_signatures)
    fingerprint = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"docs_{fingerprint}"

def check_existing_collection(collection_name, chroma_client):
    """Vérifier si une collection existe et est valide"""
    try:
        collection = chroma_client.get_collection(name=collection_name)
        count = collection.count()
        
        if count > 0:
            st.success(f"✅ Collection trouvée: {collection_name} ({count} chunks)")
            return collection, True
        else:
            # Collection vide, la supprimer
            try:
                chroma_client.delete_collection(name=collection_name)
            except:
                pass
            return None, False
            
    except Exception:
        return None, False

def cleanup_old_session_collections(chroma_client):
    """Nettoyer les anciennes collections de session"""
    try:
        collections = chroma_client.list_collections()
        
        for collection in collections:
            # Supprimer les anciennes collections de session (format obsolète)
            if collection.name.startswith("rag_sections_") and len(collection.name) > 20:
                try:
                    chroma_client.delete_collection(name=collection.name)
                    st.info(f"🗑️ Nettoyage collection obsolète: {collection.name[:20]}...")
                except:
                    pass
    except Exception:
        pass

def create_or_reuse_index(selected_files, documents):
    """Logique principale : créer ou réutiliser un index"""
    
    # 1. Calculer l'empreinte des documents sélectionnés
    collection_name = get_document_fingerprint(selected_files)
    
    # 2. Connexion ChromaDB
    chroma_host = os.environ.get("CHROMA_HOST", "chromadb")
    chroma_port = int(os.environ.get("CHROMA_PORT", "8000"))
    
    try:
        chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        
        # Nettoyage préventif des anciennes collections
        cleanup_old_session_collections(chroma_client)
        
        # 3. Vérifier si collection existe
        existing_collection, exists = check_existing_collection(collection_name, chroma_client)
        
        if exists and existing_collection:
            # 🚀 RÉUTILISATION : Collection trouvée !
            st.success("🚀 **Réutilisation de l'index existant** - Pas de ré-indexation nécessaire !")
            
            vector_store = ChromaVectorStore(chroma_collection=existing_collection)
            
            # Créer l'index depuis le vector store existant
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=get_embed_model()
            )
            
            return index, "reused"
        
        else:
            # 🔄 CRÉATION : Nouvelle indexation nécessaire
            st.info(f"🔄 **Création d'un nouvel index** ({collection_name})")
            
            # Créer nouvelle collection
            collection = chroma_client.create_collection(name=collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            
            # Indexer les documents
            node_parser = MarkdownNodeParser(chunk_size=512)
            index = VectorStoreIndex.from_documents(
                documents=documents,
                vector_store=vector_store,
                transformations=[node_parser],
                embed_model=get_embed_model(),
                show_progress=True
            )
            
            st.success(f"✅ **Index créé avec succès** - Sera réutilisé pour les prochaines sessions")
            return index, "created"
    
    except Exception as e:
        # Fallback vers vector store en mémoire
        st.warning(f"ChromaDB non disponible ({e})")
        st.info("🔄 Utilisation d'un index en mémoire...")
        
        node_parser = MarkdownNodeParser(chunk_size=512)
        index = VectorStoreIndex.from_documents(
            documents=documents,
            transformations=[node_parser],
            embed_model=get_embed_model(),
            show_progress=True
        )
        
        return index, "memory"

def extract_sections(md: str, levels=["##"]):
    sections = []
    current = []
    for line in md.splitlines(keepends=True):
        if any(line.startswith(level) for level in levels):
            if current:
                sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))
    return sections

def read_document(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in [".docx", ".pdf"]:
        reader = DoclingReader()
        nodes = reader.load_data(file_path)
        return "\n".join([node.text for node in nodes])
    elif ext in [".txt", ".md"]:
        return Path(file_path).read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported format: {ext}")

def clean_section_title(title: str) -> str:
    """Clean and extract meaningful title from section content"""
    # Remove markdown formatting
    clean_title = re.sub(r'^#+\s*', '', title.strip())
    # Take first line only
    clean_title = clean_title.split('\n')[0]
    # Limit length
    return clean_title[:80] + "..." if len(clean_title) > 80 else clean_title

def create_section_summary(content: str, max_length: int = 150) -> str:
    """Create a smart summary of section content"""
    # Remove markdown formatting and extra whitespace
    clean_content = re.sub(r'[#*_`]', '', content)
    clean_content = ' '.join(clean_content.split())
    
    # Try to get first complete sentence
    sentences = clean_content.split('.')
    if sentences and len(sentences[0]) < max_length and sentences[0].strip():
        return sentences[0].strip() + "."
    else:
        return clean_content[:max_length].strip() + "..."

def render_section_selection_ui(sections_by_doc):
    """Render section selection UI by document"""
    
    st.markdown("### Selection by Document")
    
    for doc_name, sections in sections_by_doc.items():
        with st.expander(f"📄 {doc_name} ({len(sections)} sections)", expanded=False):
            
            # Document-level controls
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Select all from {doc_name}", key=f"select_doc_{doc_name}"):
                    for idx in range(1, len(sections) + 1):
                        if (doc_name, idx) not in st.session_state.selected_sections_final:
                            st.session_state.selected_sections_final.append((doc_name, idx))
                    st.rerun()
            
            with col2:
                if st.button(f"Deselect all from {doc_name}", key=f"deselect_doc_{doc_name}"):
                    st.session_state.selected_sections_final = [
                        (d, i) for d, i in st.session_state.selected_sections_final if d != doc_name
                    ]
                    st.rerun()
            
            # Individual sections
            for idx, section_content in enumerate(sections, 1):
                title = clean_section_title(section_content.splitlines()[0] if section_content.splitlines() else f"Section {idx}")
                summary = create_section_summary(section_content)
                is_selected = (doc_name, idx) in st.session_state.selected_sections_final
                
                col1, col2 = st.columns([1, 6])
                with col1:
                    if st.checkbox("", value=is_selected, key=f"doc_{doc_name}_{idx}"):
                        if (doc_name, idx) not in st.session_state.selected_sections_final:
                            st.session_state.selected_sections_final.append((doc_name, idx))
                    else:
                        if (doc_name, idx) in st.session_state.selected_sections_final:
                            st.session_state.selected_sections_final.remove((doc_name, idx))
                
                with col2:
                    st.markdown(f"**Section {idx}: {title}**")
                    st.caption(summary)

def render_current_selection():
    """Render current selection summary"""
    if st.session_state.selected_sections_final:
        st.markdown("### 📋 Current Selection")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Selected {len(st.session_state.selected_sections_final)} sections")
        with col2:
            if st.button("Clear All", key="clear_selection"):
                st.session_state.selected_sections_final = []
                st.rerun()
        
        # Group by document for better display
        by_doc = {}
        for doc_name, idx in st.session_state.selected_sections_final:
            if doc_name not in by_doc:
                by_doc[doc_name] = []
            by_doc[doc_name].append(idx)
        
        for doc_name, indices in by_doc.items():
            st.markdown(f"**📄 {doc_name}:** Sections {', '.join(map(str, sorted(indices)))}")

# Main App
st.set_page_config(page_title="RAG App", page_icon="📚", layout="wide")

st.title("📚 RAG App: Smart Document Q&A")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    mode = st.radio("Choose LLM mode:", ["Local (Ollama)", "OpenAI API"])
    
    st.header("📁 Document Selection")
    if not Path(DATA_DIR).exists():
        st.error(f"Data directory '{DATA_DIR}' not found!")
        st.stop()

    files = list(Path(DATA_DIR).glob("*.docx")) + list(Path(DATA_DIR).glob("*.pdf")) + list(Path(DATA_DIR).glob("*.txt")) + list(Path(DATA_DIR).glob("*.md"))
    file_names = [f.name for f in files]

    if not file_names:
        st.warning(f"No supported files found in '{DATA_DIR}' directory!")
        st.stop()

    selected_files = st.multiselect("Choose files to index", file_names)
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        reset_chat()

if selected_files:
    with st.spinner("🔄 Processing documents..."):
        # Parse documents and extract sections
        documents = []
        doc_sections = {}
        
        for fname in selected_files:
            fpath = str(Path(DATA_DIR) / fname)
            try:
                md_content = read_document(fpath)
                sections = extract_sections(md_content)
                doc_sections[fname] = sections
                
                # Create Document objects for indexing
                for idx, section_content in enumerate(sections):
                    doc = Document(
                        text=section_content,
                        metadata={
                            "file": fname,
                            "section": idx + 1,
                            "source": fpath
                        }
                    )
                    documents.append(doc)
                    
            except Exception as e:
                st.error(f"Error reading {fname}: {e}")
                continue
        
        if not documents:
            st.error("No documents could be processed!")
            st.stop()
    
    # 🧠 INDEXATION INTELLIGENTE
    try:
        with st.spinner("🔍 Checking for existing index..."):
            index, status = create_or_reuse_index(selected_files, documents)
            
        # Affichage du statut
        if status == "reused":
            st.success("⚡ **Index réutilisé** - Gain de temps significatif !")
        elif status == "created":
            st.success("✅ **Nouvel index créé** - Sera réutilisé pour les prochaines utilisations !")
        else:  # memory
            st.info("💾 **Index en mémoire** - Sera recréé à chaque session")
            
    except Exception as e:
        st.error(f"Error during indexing: {e}")
        st.stop()

    # Section Selection UI
    st.header("🎯 Section Selection")
    
    render_section_selection_ui(doc_sections)
    render_current_selection()
    
    # Chat interface
    st.header("💬 Chat with Documents")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Build retriever filter if sections selected
                filter_kwargs = {}
                if st.session_state.selected_sections_final:
                    allowed_sections = set(st.session_state.selected_sections_final)
                    
                    def section_filter(node):
                        meta = node.metadata
                        return (meta.get("file"), meta.get("section")) in allowed_sections
                    
                    filter_kwargs["node_filter"] = section_filter

                # LLM selection
                llm = load_local_llm() if mode == "Local (Ollama)" else load_openai_llm()
                Settings.llm = llm
                
                # Create prompt template
                rag_prompt = PromptTemplate(RAG_PROMPT)
                
                # Create query engine
                query_engine = index.as_query_engine(
                    streaming=True,
                    similarity_top_k=4,
                    text_qa_template=rag_prompt,
                    **filter_kwargs
                )
                
                # Execute query
                streaming_response = query_engine.query(prompt)
                
                # Show retrieved context
                if hasattr(streaming_response, 'source_nodes') and streaming_response.source_nodes:
                    with st.expander("📚 Retrieved Context", expanded=False):
                        for i, ctx in enumerate(streaming_response.source_nodes):
                            st.markdown(f"**Source {i+1}:** {ctx.metadata.get('file', 'unknown')} (Section {ctx.metadata.get('section', 'unknown')})")
                            st.markdown(ctx.text[:500] + ("..." if len(ctx.text) > 500 else ""))
                            st.divider()
                
                # Stream response
                for chunk in streaming_response.response_gen:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                    
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"Error during query: {e}")
                message_placeholder.markdown("Sorry, I encountered an error while processing your question.")

else:
    st.info("👈 Please select documents from the sidebar to get started!")