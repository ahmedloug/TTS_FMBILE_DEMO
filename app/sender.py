import socket
import time

HOST = "10.10.1.123"
PORT = 9696
SEND_DELAY_MS = 100  # 0.1 seconde entre chaque message
NB_MESSAGES = 40     # Nombre total de messages à envoyer

def main():
    """
    Envoie une séquence couvrant tous les cas d'usage :
    - Vitesse stable (pas de répétition TTS)
    - Changement de vitesse
    - Update mission refusé
    - Stop
    - Bip lent (dt=1)
    - Bip rapide (dt=5)
    - Arrêt du bip
    """
    sequence = [
        # Vitesse stable (ne doit être dit qu'une fois)
        {"vitesse": 30, "update_refuse": 0, "dt": 0},
        {"vitesse": 30, "update_refuse": 0, "dt": 0},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        {"vitesse": 30, "update_refuse": 2, "dt": 5},
        {"vitesse": 30, "update_refuse": 0, "dt": 5},
        # Changement de vitesse
        {"vitesse": 50, "update_refuse": 0, "dt": 0},
        {"vitesse": 50, "update_refuse": 0, "dt": 0},
        # Update mission refusé (doit dire vitesse puis refus)
        {"vitesse": 50, "update_refuse": 1, "dt": 0},
        # Retour à la normale
        {"vitesse": 50, "update_refuse": 0, "dt": 0},
        # Stop (doit dire "Stop")
        {"vitesse": 0, "update_refuse": 0, "dt": 0},
        {"vitesse": 0, "update_refuse": 0, "dt": 0},
        # Bip lent (dt=1)
        {"vitesse": 60, "update_refuse": 0, "dt": 1},
        {"vitesse": 60, "update_refuse": 0, "dt": 1},
        {"vitesse": 60, "update_refuse": 0, "dt": 1},
        # Bip rapide (dt=5)
        {"vitesse": 60, "update_refuse": 0, "dt": 5},
        {"vitesse": 60, "update_refuse": 0, "dt": 5},
        {"vitesse": 60, "update_refuse": 0, "dt": 5},
        # Arrêt du bip
        {"vitesse": 60, "update_refuse": 0, "dt": 0},
        {"vitesse": 60, "update_refuse": 0, "dt": 0},
        # Changement de vitesse avec bip
        {"vitesse": 80, "update_refuse": 0, "dt": 2},
        {"vitesse": 80, "update_refuse": 0, "dt": 2},
        # Update mission refusé avec bip
        {"vitesse": 80, "update_refuse": 1, "dt": 2},
        # Stop avec bip
        {"vitesse": 0, "update_refuse": 0, "dt": 2},
        {"vitesse": 0, "update_refuse": 0, "dt": 2},
        # Retour à vitesse normale sans bip
        {"vitesse": 40, "update_refuse": 0, "dt": 0},
        {"vitesse": 40, "update_refuse": 0, "dt": 0},
        # Bip très rapide
        {"vitesse": 40, "update_refuse": 0, "dt": 10},
        {"vitesse": 40, "update_refuse": 0, "dt": 10},
        # Arrêt du bip
        {"vitesse": 40, "update_refuse": 0, "dt": 0},
        # Update mission refusé sans bip
        {"vitesse": 40, "update_refuse": 1, "dt": 0},
        # Stop final
        {"vitesse": 0, "update_refuse": 0, "dt": 0},
    ]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connecté à {HOST}:{PORT}")
        for idx in range(NB_MESSAGES):
            cmd = sequence[idx % len(sequence)]
            vitesse = cmd["vitesse"]
            update_refuse = cmd["update_refuse"]
            dt = cmd["dt"]

            vecteur = bytes([vitesse, update_refuse, dt])
            binaires = ' '.join(f'{b:08b}' for b in vecteur)
            print(f"Envoyé : vitesse={vitesse}, update_refuse={update_refuse}, dt={dt} | binaires: {binaires}")
            s.sendall(vecteur)
            time.sleep(SEND_DELAY_MS / 1000.0)

if __name__ == "__main__":
    main()