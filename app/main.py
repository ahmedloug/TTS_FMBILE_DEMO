import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.text_splitter import CharacterTextSplitter
import os


# URL processing
def process_input(urls, question):
    # Utilise l'URL Ollama depuis la variable d'environnement ou valeur par défaut
    ollama_url = os.environ.get("OLLAMA", "http://ollama:11434")
    model_local = Ollama(model="mistral:7b", base_url=ollama_url)
    
    # Convert string of URLs to list
    urls_list = [u.strip() for u in urls.split("\n") if u.strip()]
    docs = [WebBaseLoader(url).load() for url in urls_list]
    docs_list = [item for sublist in docs for item in sublist]
    
    # Split the text into chunks
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=7500, chunk_overlap=100)
    doc_splits = text_splitter.split_documents(docs_list)
    
    # Convert text chunks into embeddings and store in vector database
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding=OllamaEmbeddings(
            model='nomic-embed-text',
            base_url=ollama_url
        ),
    )
    retriever = vectorstore.as_retriever()
    
    # RAG prompt and chain
    after_rag_template = """Réponds à la question en te basant uniquement sur le contexte suivant. 
Réponds en français de manière claire et structurée.

Contexte:
{context}

Question: {question}

Instructions:
- Utilise seulement les informations du contexte fourni
- Si l'information n'est pas dans le contexte, dis "L'information n'est pas disponible dans les documents fournis"
- Réponds de manière concise mais complète
- Utilise un langage clair et professionnel

Réponse:"""
    after_rag_prompt = ChatPromptTemplate.from_template(after_rag_template)
    after_rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | after_rag_prompt
        | model_local
        | StrOutputParser()
    )
    return after_rag_chain.invoke(question) 


# Streamlit app
st.title("RAG MINIMAL OLLAMA")
st.write("Enter URLs (one per line) and a question to query the documents.")

# Input fields
urls = st.text_area("Enter URLs separated by new lines", height=150)
question = st.text_input("Question")

# Button to process input
if st.button('Query Documents'):
    with st.spinner('Processing...'):
        answer = process_input(urls, question)
        st.text_area("Answer", value=answer, height=300, disabled=True)