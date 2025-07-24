# import torch

# print(torch.cuda.is_available())
# print(torch.cuda.device_count())

import os
from pathlib import Path
from typing import List, Optional

import streamlit as st
from dotenv import load_dotenv
from llama_index.readers.docling import DoclingReader

from fpdf import FPDF


def create_dummy_pdf(file_path: str):
    """
    Crée un fichier PDF valide avec du contenu minimal.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Dummy PDF content for initialization.", ln=True, align="C")
    pdf.output(file_path)

def initialize_docling():
    """
    Initialise DoclingReader pour forcer le téléchargement des modèles nécessaires.
    """
    try:
        dummy_pdf = "/tmp/dummy.pdf"
        create_dummy_pdf(dummy_pdf)  # Crée un fichier PDF valide
        reader = DoclingReader()
        reader.load_data(dummy_pdf)
        Path(dummy_pdf).unlink()  # Supprime le fichier temporaire
    except Exception as e:
        st.warning(f"Erreur lors de l'initialisation de DoclingReader : {e}")

# Appelle cette fonction au début du script
initialize_docling()