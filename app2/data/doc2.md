# doc02_bluetooth_comm_module.md

## 1. Présentation et contexte  
Le module **BlueLink** implémente une connectivité Bluetooth Low Energy 5.0 pour un dispositif médical portable. L’objectif est de le lier à une application mobile pour le suivi des mesures biométriques en temps réel.

## 2. Caractéristiques matérielles  
- **Chipset** : Nordic nRF52840 (SoC ARM Cortex‑M4, 64 MHz, 1 MB FLASH, 256 kB RAM).  
- **Antenne** : PCB traceée, hauteur 2 mm, gain 1,8 dBi.  
- **Alimentation** : 1,8–3,6 V, consommation typique 8 mA en active, 2 µA en veille profonde.  

## 3. Architecture logicielle  
1. **SoftDevice S140** : pile BLE officielle Nordic, gestion du lien, sécurité.  
2. **Profil GATT** :  
   - Service « HealthData » (UUID custom), caractéristiques lecture/écriture :  
     - `0x2A6E` (Température)  
     - `0x2A37` (Fréquence cardiaque)  
   - Notifications et indications supportées.  
3. **Sécurité** : pairing Just Works ou Passkey Entry, cryptage AES-128 FIPS-197.  
4. **Mode low‑power** : advertise à 1 Hz pendant 30 s puis 0,1 Hz en inactivité.  
5. **Mise à jour OTA** : DFU via BLE avec confiance renforcée (signature ECDSA).  

## 4. Exigences techniques détaillées  
- **REQ-BL-001 :** Débit GATT ≥ 1,2 Mbit/s mesuré sur 1 Mo de data.  
- **REQ-BL-002 :** Latence de connexion initiale ≤ 50 ms (scan + connexion).  
- **REQ-BL-003 :** Taux PER < 0,1 % sur 10 min de transmission continue.  
- **REQ-BL-004 :** Consommation ≤ 10 mA en connexion active, ≤ 5 µA en publicité low‑power.  
- **REQ-BL-005 :** Sécurité AES-128 end-to-end, authentification mutuelle.  
- **REQ-BL-006 :** Support de 20 connexions simultanées sans dégradation > 10 %.  

## 5. Contraintes environnementales  
- **Température** : –20 °C → +70 °C.  
- **Humidité** : 5 % → 95 % sans condensation.  
- **Vibrations/Chocs** : 3 g, 10–200 Hz / 50 g, 11 ms.  

## 6. Scénarios et protocoles de test  
### 6.1 Test de débit GATT  
- Envoyer un fichier de 1 Mo en chunk 20 kB, mesurer temps total et débit moyen.  
- Critère : ≥ 1,2 Mbit/s.  

### 6.2 Latence de connexion  
- Effacer paires, lancer scan, connexion, échange de MTU, mesurer durée.  
- Critère : ≤ 50 ms.  

### 6.3 Test PER et robustesse  
- Transmission continue pendant 10 min, injection de bruit RF (3 V/m).  
- Mesurer PER, doit rester < 0,1 %.  

### 6.4 Test multi‑connexion  
- Connecter 20 clients simulés, each subscribing to notifications.  
- Mesurer latence de notification moyenne et CPU load.  
- Critère : latence < 100 ms, utilisation CPU < 70 %.  

### 6.5 Sécurité et DFU  
- Tentative de DFU non signé, vérifier refus.  
- Mise à jour firmware signé, mesurer temps de DFU et impact mémoire.  

## 7. Résultats et journalisation  
| Date       | Test                    | Paramètres               | Résultat    | Notes                      |
|------------|-------------------------|--------------------------|-------------|----------------------------|
| 2025-06-05 | Débit GATT              | 1 Mo, 20 kB chunks       | 1,25 Mbit/s | OK                         |
| 2025-06-10 | Connexion initiale      | Pairings vides           | 48 ms       | OK                         |
| 2025-06-15 | PER 10 min + bruit RF   | 3 V/m                    | 0,08 %      | OK                         |
| 2025-06-20 | 20 connexions simult.   | CPU load 65 %            | OK          | Latence notif 85 ms        |
| 2025-06-25 | DFU signé/non signé     | Firmware 128 kB          | OK/Refus    | Temps DFU 2 min            |

## 8. Maintenance et mises à jour  
- **Recalage antenne** : tous les 12 mois ou après choc important.  
- **Mises à jour SoftDevice** : compatible backward, test de régression.  
- **Audit de sécurité** : annuel, tests de fuzzing BLE.
