# -----------------------------------------------------------------------------
# FastAPI Text-to-Speech (TTS) API utilisant Piper
#
# Ce script expose une API FastAPI sur /tts qui prend un texte en entrée,
# génère un fichier audio .wav avec Piper TTS, le joue automatiquement sur
# la sortie audio de la machine (via PulseAudio/paplay), et renvoie le
# fichier audio au client.
#
# Fonctionne en tandem avec le listener TCP (listener.py) qui déclenche
# la synthèse vocale en fonction des commandes réseau reçues.
#
# Prérequis :
# - Le modèle Piper doit être présent dans le dossier "models"
# - Le conteneur doit avoir accès à la carte son de l’hôte (ex: --device=/dev/snd)
# - PulseAudio doit être accessible (PULSE_SERVER)
# -----------------------------------------------------------------------------

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
import subprocess
import os
import hashlib

app = FastAPI()

def synthesize_speech(
    text: str,
    voice: str = "en_US-amy-medium",  # Voix par défaut
    models_dir: str = os.path.join(os.path.dirname(__file__), "models"),
    output_file: str = "welcome.wav"
):
    """
    Génère un fichier audio WAV à partir d'un texte en utilisant Piper.
    Utilisé pour la synthèse vocale à la demande.
    """
    model_path = os.path.join(models_dir, f"{voice}.onnx")
    config_path = os.path.join(models_dir, f"{voice}.onnx.json")

    if not os.path.isfile(model_path) or not os.path.isfile(config_path):
        raise FileNotFoundError(f"Model or config not found in {models_dir}")

    # Crée le dossier de sortie si besoin
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Appelle Piper pour générer le fichier audio
    subprocess.run(
        [
            "piper",
            "--model", model_path,
            "--config", config_path,
            "--output_file", output_file
        ],
        input=text.encode("utf-8"),
        check=True
    )
    print(f"Audio saved to {output_file}")

def play_audio(file_path: str):
    """
    Joue un fichier audio WAV sur la sortie son (PulseAudio).
    Utilisé pour diffuser la synthèse vocale sur le haut-parleur.
    """
    subprocess.run(["paplay", file_path])

def text_to_filename(text, output_dir):
    """
    Génère un nom de fichier unique pour chaque texte (cache) via un hash SHA256.
    Permet de réutiliser un fichier déjà généré pour le même texte.
    """
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return os.path.join(output_dir, f"{h}.wav")

@app.get("/tts")
def tts(
    text: str = Query(..., min_length=1, description="Texte à synthétiser")
):
    """
    Endpoint principal de l'API.
    - Reçoit un texte en paramètre GET.
    - Génère (ou récupère depuis le cache) le fichier audio correspondant.
    - Joue le fichier audio sur la machine serveur.
    - Retourne le fichier WAV au client.
    """
    voice = "en_US-amy-medium"  # modèle utilisé
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = text_to_filename(text, output_dir)

    # Logique de cache : si le fichier existe déjà, on le réutilise
    if not os.path.isfile(output_path):
        try:
            synthesize_speech(text, voice=voice, output_file=output_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        print(f"Utilisation du cache pour : {text}")

    play_audio(output_path)  # Joue le fichier audio sur le serveur

    return FileResponse(
        output_path,
        media_type="audio/wav",
        filename="speech.wav"
    )