# -----------------------------------------------------------------------------
# Listener TCP pour commandes TTS & Bips
#
# Ce script écoute sur un port TCP (9696) et reçoit des commandes binaires
# (vitesse, update_refuse, dt) envoyées par un client (sender.py ou autre).
# Selon la commande reçue, il déclenche la synthèse vocale (via l'API FastAPI)
# et/ou la génération de bips sonores à la fréquence demandée.
#
# Fonctionne en tandem avec main.py (serveur TTS FastAPI).
# -----------------------------------------------------------------------------

import socket
import requests
import threading
import time
import subprocess
import os

TTS_API_URL = "http://localhost:8000/tts?text={}"  # API FastAPI locale
PORT = 9696  # Port TCP d'écoute

def call_tts(text):
    """
    Appelle l'API TTS pour synthétiser et jouer un texte.
    Utilisé pour annoncer la vitesse, l'état ou les messages système.
    """
    url = TTS_API_URL.format(requests.utils.quote(text))
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"Erreur appel TTS: {e}")

def vitesse_to_text(vitesse):
    """
    Convertit la valeur de vitesse en texte (pour l'API TTS).
    """
    return f"{vitesse}"

def update_refuse_text():
    """
    Texte à prononcer si la mission est refusée.
    """
    return "Rejected"

def update_accept_text():
    """
    Texte à prononcer si la mission est acceptée.
    """
    return "Accepted"

def play_beep_audible():
    """
    Joue un bip audible sur la sortie son.
    - Utilise bip.wav si présent, sinon génère un bip avec sox/play.
    """
    try:
        if os.path.exists("bip.wav"):
            subprocess.run(["paplay", "bip.wav"], 
                         stderr=subprocess.DEVNULL, check=False)
            return
        
        # Génère un bip avec sox (si bip.wav absent)
        result = subprocess.run([
            "sox", "-n", "-t", "alsa", "default", 
            "synth", "0.3", "sine", "800", "gain", "-5"
        ], stderr=subprocess.DEVNULL, check=False)
        
        if result.returncode != 0:
            # Si sox échoue, tente avec play
            subprocess.run([
                "play", "-n", "synth", "0.3", "sine", "800", "gain", "-5"
            ], stderr=subprocess.DEVNULL, check=False)
            
    except Exception as e:
        print(f"Erreur beep: {e}")
        print("\a")  # Bip système de secours

def bip_loop(dt, stop_event):
    """
    Joue des bips à la fréquence dt (bips/seconde) tant que stop_event n'est pas activé.
    """
    if dt <= 0:
        return
    
    interval = 1.0 / dt
    while not stop_event.is_set():
        play_beep_audible()
        start_time = time.time()
        while time.time() - start_time < interval:
            if stop_event.is_set():
                return
            time.sleep(0.01)

def main():
    """
    Boucle principale : écoute sur le port TCP, reçoit les commandes binaires,
    gère la synthèse vocale et les bips selon le protocole décrit dans le README.
    """
    print(f"En écoute sur le port {PORT}...")  # Affiche que le serveur est prêt
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", PORT))
        s.listen()
        
        while True:
            conn, addr = s.accept()
            with conn:
                last_msg = None
                current_bip_thread = None
                current_bip_stop = None

                while True:
                    data = conn.recv(3)
                    if not data or len(data) < 3:
                        # Arrêt des bips si la connexion se termine
                        if current_bip_stop:
                            current_bip_stop.set()
                        if current_bip_thread and current_bip_thread.is_alive():
                            current_bip_thread.join()
                        break

                    vitesse, update_refuse, dt = data[0], data[1], data[2]
                    current_msg = (vitesse, update_refuse, dt)

                    # Gestion des bips : redémarre le thread si la fréquence change
                    if last_msg is None or last_msg[2] != dt:
                        if current_bip_stop:
                            current_bip_stop.set()
                        if current_bip_thread and current_bip_thread.is_alive():
                            current_bip_thread.join()
                        if dt > 0:
                            current_bip_stop = threading.Event()
                            current_bip_thread = threading.Thread(
                                target=bip_loop, 
                                args=(dt, current_bip_stop)
                            )
                            current_bip_thread.daemon = True
                            current_bip_thread.start()
                        else:
                            current_bip_stop = None
                            current_bip_thread = None

                    # LOGIQUE TTS : annonce selon le changement de message
                    if current_msg != last_msg:
                        # Si la vitesse est 0, on annonce "Stop"
                        if vitesse == 0:
                            call_tts("Stop")
                        # Si la mission change (update_refuse == 1 ou 2), on annonce la décision
                        elif update_refuse == 1:
                            call_tts(update_accept_text())
                        elif update_refuse == 2:
                            call_tts(update_refuse_text())
                        # Sinon, on annonce la nouvelle vitesse
                        elif vitesse != (last_msg[0] if last_msg else None):
                            call_tts(vitesse_to_text(vitesse))
                    last_msg = current_msg

if __name__ == "__main__":
    main()