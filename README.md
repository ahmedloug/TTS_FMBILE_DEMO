# TTS_FMBILE – Synthèse Vocale & Bips en Temps Réel  
Déploiement et Fonctionnement sur Jetson ARM

Ce document décrit le fonctionnement du projet **TTS_FMBILE** (Text-to-Speech & Beep System), son architecture réseau, ainsi que les étapes pour le déployer sur une NVIDIA Jetson sous Ubuntu ARM avec démarrage automatique.

---

## 1. Présentation et Fonctionnement Global

Le système permet de générer de la synthèse vocale (TTS) et des bips sonores en temps réel, en réponse à des commandes réseau. Il est conçu pour fonctionner dans un environnement embarqué (Jetson), avec gestion de l’audio via PulseAudio.

### Architecture Logicielle

Le projet est composé de **3 composants principaux** :

1. **Serveur TTS** ([app/main.py](app/main.py))  
   API FastAPI qui convertit du texte en parole (WAV) via Piper.
2. **Listener** ([app/listener.py](app/listener.py))  
   Écoute les commandes réseau (TCP), déclenche la synthèse vocale et/ou les bips.
3. **Sender** ([app/sender.py](app/sender.py))  
   Simule l’envoi de commandes (vitesse, état, fréquence des bips) pour tests.

> **Remarque :**  
> Le lancement du serveur TTS et du listener est automatisé grâce au `Dockerfile` du projet, qui exécute le script `start.sh` lors du démarrage du conteneur. Ce script se charge de démarrer à la fois l’API FastAPI (serveur) et le listener TCP.

### Architecture Réseau

Le système utilise une communication **TCP socket** sur le port `9696` :

```
Sender ──[TCP:9696]──> Listener ──[HTTP:8000]──> Serveur TTS
  │                        │                         │
  │                        │                         ▼
  │                        ▼                    Génération WAV
  │                   Décodage commande             │
  │                   [vitesse|refus|dt]            │
  │                        │                        │
  │                        ▼                        │
  │                 Logique Audio ◄─────────────────┘
  │                   TTS + Bips
  │
  ▼
Messages format:
[vitesse: 0-255] [update_refuse: 0/1] [dt: 0-255 bips/sec]
```

- **Sender** envoie des messages binaires (3 octets) : vitesse, update_refuse, dt.
- **Listener** reçoit, interprète, et déclenche :
  - Synthèse vocale via requête HTTP au serveur TTS.
  - Lecture de bips à la fréquence demandée.
- **Serveur TTS** génère le fichier audio WAV et le joue sur la sortie son.

---

## 2. Déploiement sur Jetson ARM

### 2.1 Pré-requis

- Docker installé sur la Jetson (ARM64)
- Accès à la carte son (`--device /dev/snd`)
- PulseAudio installé sur l’hôte

### 2.2 Construction de l’image Docker

```bash
cd /chemin/vers/projet
sudo docker build -t demo:v0 .
```

Le [Dockerfile](app/Dockerfile) installe les dépendances Python et audio nécessaires (`curl`, `sox`, `pulseaudio-utils`) et configure le point d’entrée pour lancer automatiquement le serveur et le listener via le script `start.sh`.

### 2.3 Lancement manuel (pour tests)

Sur la Jetson :

```bash
# Exposer PulseAudio en TCP (une fois)
pactl load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1

# Lancer le container
sudo docker run -it --rm \
  --name tts_fmbile \
  --network host \
  --device /dev/snd \
  -e PULSE_SERVER=tcp:127.0.0.1:4713 \
  demo:v0

# Dans le container, pour tester l’audio :
apt update && apt install -y pulseaudio-utils sox
paplay /usr/share/sounds/alsa/Front_Center.wav
```

### 2.4 Démarrage automatique au boot

Pour lancer le module TTS (serveur + listener) au démarrage, ajoutez dans `~/.bashrc` (ou `/home/nvidia/.profile`) :

```bash
# Module TTS
pactl load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1 
sudo docker run -it --rm \
  --name tts_fmbile \
  --network host \
  --device /dev/snd \
  -e PULSE_SERVER=tcp:127.0.0.1:4713 \
  demo:v0
```

- `pactl load-module` : expose PulseAudio en TCP (silencieux si déjà chargé)

> **Note :**  
> Grâce au `Dockerfile`, le script `start.sh` est exécuté automatiquement à chaque lancement du conteneur, ce qui assure le démarrage du serveur FastAPI et du listener TCP sans intervention manuelle.

### 2.5 Vérification

Après un reboot :

```bash
sudo docker ps | grep tts_fmbile
```

Si tout est OK, le serveur **Uvicorn** (API FastAPI) et le **listener** seront actifs, et la commande `paplay un_fichier.wav` fonctionnera.

---

## 3. Format des Messages

Chaque message envoyé au listener est un vecteur de 3 octets :

- **vitesse** : 0–255
- **update_refuse** : 0 (rien), 1 (accepted), 2 (rejected)
- **dt** : nombre de bips/seconde (0 = pas de bip)

Exemple d’envoi :  
Voir [app/sender.py](app/sender.py) pour la génération des séquences de test.

---

## 4. Fonctionnalités Audio

- Synthèse vocale multilingue via Piper ([app/models/](app/models/))
- Lecture de fichiers WAV sur la sortie son (PulseAudio/ALSA)
- Bips audibles à fréquence paramétrable

---

## 5. Dockerhub

Pour déployer ce projet sur une autre machine, il n'est pas nécessaire de reconstruire l'image Docker : il suffit de la télécharger depuis DockerHub et rajouter dans le .bashrc les commandes necessaires . 

L'image officielle est disponible ici :  
[https://hub.docker.com/repository/docker/louug/tts/general](https://hub.docker.com/repository/docker/louug/tts/general)

- **Tag `v0`** : c'est la version utilisée lors de la démonstration du 10 juillet 2025.
- **Tag `v0.1averifier`**: ne repète pas la vitesse lors d'un updtae mission.

### Étapes pour utiliser l'image DockerHub

1. **Récupérer l'image depuis DockerHub :**
   ```bash
   sudo docker pull louug/tts:v0
   ```
   *(ou remplacer `v0` par `v0.1` selon le comportement souhaité)*

2. **Lancer le conteneur :**
   - **En manuel :**
     ```bash
     sudo docker run -it --rm \
       --name tts_fmbile \
       --network host \
       --device /dev/snd \
       -e PULSE_SERVER=tcp:127.0.0.1:4713 \
       louug/tts:v0
     ```
   - **En automatique (exemple dans `.bashrc`) :**
     ```bash
     pactl load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1
     sudo docker run -d --rm \
       --name tts_fmbile \
       --network host \
       --device /dev/snd \
       -e PULSE_SERVER=tcp:127.0.0.1:4713 \
       louug/tts:v0
     ```

> **Remarque :**  
> Pensez à ajouter l’option de volume `-v tts_cache:/app/output` si vous souhaitez conserver le cache audio entre les redémarrages du conteneur (voir section 6).

En résumé, il suffit de faire un `docker pull` de l’image souhaitée, puis de lancer le conteneur comme décrit ci-dessus, pour retrouver exactement le même environnement que celui utilisé lors de la démonstration.

---

## 6. Ameliorations possibles

### Pour activer la persistance du cache audio :

1. Crée un volume Docker :
   ```bash
   sudo docker volume create tts_cache
   ```

2. Modifier la commande de lancement du conteneur (dans `.bashrc`):
   ```bash
   pactl load-module module-native-protocol-tcp auth-ip-acl=127.0.0.1
   sudo docker run -it --rm \
     --name tts_fmbile \
     --network host \
     --device /dev/snd \
     -e PULSE_SERVER=tcp:127.0.0.1:4713 \
     -v tts_cache:/app/output \
     demo:v0
   ```

3. Les fichiers WAV générés seront désormais conservés entre chaque redémarrage du conteneur.

> **À noter :**  
> Le volume Docker `tts_cache` doit être créé une seule fois sur la machine. Il sera automatiquement réutilisé à chaque lancement du conteneur, ce qui permet de conserver le cache audio même après un redémarrage ou une suppression du conteneur.

### Question ouverte : Est ce que mon modèle dans le contenaire a accès à CUDA

---

## 7. Alternative : Déploiement simplifié avec Docker Compose

Pour simplifier la gestion du volume, du lancement du conteneur et de la configuration, il est possible d’utiliser **Docker Compose**.  
Cette méthode permet de définir tous les paramètres (image, volume, variables d’environnement, accès à la carte son…) dans un seul fichier (`docker-compose.yml`), ce qui facilite le déploiement, la maintenance et la reproductibilité.

### Exemple de fichier `docker-compose.yml` :

```yaml
version: "3.8"

services:
  tts_fmbile:
    image: louug/tts:v0
    container_name: tts_fmbile
    network_mode: host
    devices:
      - /dev/snd:/dev/snd
    environment:
      - PULSE_SERVER=tcp:127.0.0.1:4713
    volumes:
      - tts_cache:/app/output
    restart: unless-stopped

volumes:
  tts_cache:
```

### Utilisation

1. **Créer le fichier `docker-compose.yml`** dans le dossier de votre choix.
2. **Lancer le service :**
   ```bash
   docker compose up -d
   ```
3. **Arrêter le service :**
   ```bash
   docker compose down
   ```

### Différences et avantages par rapport à l’approche précédente

- **Centralisation :** toute la configuration (image, volume, device, variables d’environnement) est dans un seul fichier, facile à versionner et partager.
- **Simplicité :** une seule commande pour démarrer ou arrêter le service, pas besoin de répéter les options complexes de `docker run`.
- **Persistance :** le volume Docker `tts_cache` est automatiquement créé et géré par Compose.
- **Maintenance :** il est plus facile de modifier ou d’ajouter des paramètres (par exemple, changer l’image ou ajouter d’autres services).
- **Redémarrage automatique :** grâce à `restart: unless-stopped`, le service redémarre automatiquement en cas de redémarrage de la machine.

> **Remarque :**  
> Il faut toujours s’assurer que PulseAudio est bien exposé en TCP sur l’hôte avant de lancer le conteneur (voir section 2.3).

---



