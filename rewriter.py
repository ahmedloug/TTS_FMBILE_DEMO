import os
from pathlib import Path
from typing import List, Optional

import streamlit as st
from dotenv import load_dotenv
from llama_index.readers.docling import DoclingReader
from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI



# Charger les variables d'environnement depuis un fichier .env
load_dotenv()

SUPPORTED_FORMATS = [".docx", ".txt", ".md", ".pdf"]

def read_document(file_path: str) -> str:
    """
    Lit un document et extrait son contenu en texte brut ou Markdown.

    Args:
        file_path (str): Le chemin vers le fichier.

    Returns:
        str: Le contenu extrait du document.
    """
    ext = Path(file_path).suffix.lower()
    if ext in [".docx", ".pdf"]:  # DoclingReader prend en charge .docx et .pdf
        reader = DoclingReader()
        nodes = reader.load_data(file_path)
        return "\n".join([node.text for node in nodes])
    elif ext in [".txt", ".md"]:
        return Path(file_path).read_text(encoding="utf-8")
    else:
        raise ValueError(f"Format non supporté: {ext}")

def extract_sections(md: str, levels: List[str] = ["##"]) -> List[str]:
    """
    Extrait les sections d'un document Markdown en fonction des niveaux de titres spécifiés.

    Args:
        md (str): Le contenu Markdown.
        levels (List[str]): Les niveaux de titres à prendre en compte (par exemple, ["#", "##", "###"]).

    Returns:
        List[str]: Une liste de sections.
    """
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

def rewrite_text_ollama(text: str, prompt: str) -> str:
    ollama_url = os.environ.get("OLLAMA", "http://ollama:11434")
    llm = Ollama(model="mistral:7b", base_url=ollama_url, request_timeout=200)
    full_prompt = f"{prompt}\n\n{text.strip()}"
    try:
        response = llm.complete(full_prompt)
        return response.text.strip()
    except Exception as e:
        if "requires more system memory" in str(e):
            st.warning("Ollama a rencontré une erreur de mémoire. Passage à l'API GPT-4.")
            return rewrite_text_openai(text, prompt)
        else:
            raise e

def rewrite_text_openai(text: str, prompt: str) -> str:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("La clé API OpenAI n'est pas définie. Assurez-vous qu'elle est dans le fichier .env.")
    
    llm = OpenAI(api_key=openai_api_key, model="gpt-4", temperature=0.7)
    full_prompt = f"{prompt}\n\n{text.strip()}"
    response = llm.complete(full_prompt)
    return response.text.strip()

def main():
    st.title("Document Rewriter")
    st.markdown("Réécrivez des sections de vos documents (.docx, .txt, .md, .pdf) avec un prompt personnalisé.")

    
    uploaded_file = st.file_uploader("Choisissez un fichier", type=["docx", "txt", "md", "pdf"])
    if uploaded_file:
        temp_path = f"/tmp/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        try:
            md = read_document(temp_path)
        except Exception as e:
            st.error(f"Erreur lors de la lecture du document: {e}")
            return

        sections = extract_sections(md)
        if not sections:
            st.warning("Aucune section détectée (titre ##). Le document sera traité comme une seule section.")
            sections = [md]

        st.markdown("### Sections détectées")
        for idx, sec in enumerate(sections, start=1):
            title = sec.splitlines()[0].strip() if sec.splitlines() else f"Section {idx}"
            st.write(f"[{idx}] {title}")

        selected_indices = st.multiselect(
            "Sélectionnez les sections à réécrire",
            options=list(range(1, len(sections)+1)),
            format_func=lambda i: sections[i-1].splitlines()[0].strip() if sections[i-1].splitlines() else f"Section {i}"
        )

        user_prompt = st.text_area("Prompt à utiliser pour la réécriture", value="Réécris ce texte en style professionnel.")

        if st.button("Réécrire les sections sélectionnées"):
            rewritten_sections = []  # Liste pour stocker uniquement les sections réécrites
            for i in selected_indices:
                st.info(f"Réécriture de la section {i}...")
                try:
                    rewritten_section = rewrite_text_ollama(sections[i-1], user_prompt) + "\n"
                    rewritten_sections.append((i, rewritten_section))  # Stocke l'indice et la section réécrite
                except Exception as e:
                    st.error(f"Erreur lors de la réécriture de la section {i}: {e}")
            
            if rewritten_sections:
                st.success("Réécriture terminée. Voici les sections réécrites :")
                for idx, rewritten in rewritten_sections:
                    st.markdown(f"### Section {idx}")
                    st.markdown(rewritten)
            else:
                st.warning("Aucune section n'a été réécrite.")

if __name__ == "__main__":
    main()