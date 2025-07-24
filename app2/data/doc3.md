# doc03_power_supply_controller.md

## 1. Contexte et objectifs  
Le contrôleur **PowerGuard** gère la distribution d’énergie sur deux rails (5 V, 12 V) dans un véhicule autonome léger. Il doit assurer la continuité, la protection et la supervision sans intervention humaine.

## 2. Architecture matérielle  
- **Microcontrôleur** : ARM Cortex‑M3 @ 120 MHz, 512 kB Flash, 128 kB RAM.  
- **MOSFETs** : deux banques N‑channel pour commutation rapide.  
- **Sense resistors** : 0,01 Ω, précision ±1 %.  
- **Convertisseur DC-DC** : pour réguler les 12 V en 5 V.  
- **Mémoire Flash** : 256 kB pour logging d’événements.  
- **Interface** : SPI pour diagnostics, I²C pour configuration, sorties d’alarme TTL.  

## 3. Architecture logicielle  
1. **Boucle principale** : 1 kHz, lecture tensions/courants, contrôle PWM.  
2. **Protection overcurrent** : détection via seuil réglable, triggers IRQ.  
3. **Protection surtension** : surveille bus d’entrée, bascule en safe-mode.  
4. **Logger circulaire** : stocke timestamp, tension, courant, event type sur 100 entrées.  
5. **Interface SPI** : commandes READ_LOG, CLEAR_LOG, SET_THRESHOLD.  
6. **Mise à jour firmware** : via bootloader SPI, vérification CRC.  

## 4. Exigences fonctionnelles et performances  
- **REQ-PSU-001 :** Rails 5 V ± 2 %, 12 V ± 1 % sous 0–5 A.  
- **REQ-PSU-002 :** Temps de commutation 5 V→12 V < 100 µs.  
- **REQ-PSU-003 :** Seuil overcurrent réglable 1–5 A, résolution 50 mA.  
- **REQ-PSU-004 :** Coupure < 50 µs après dépassement de seuil.  
- **REQ-PSU-005 :** Logging des 100 derniers events, endurance flash > 10 000 cycles.  
- **REQ-PSU-006 :** Surveillance température interne, alerte > 85 °C.  

## 5. Contraintes opérationnelles  
- **Température** : –20 °C → +85 °C.  
- **Vibrations** : 10 g, 20–200 Hz.  
- **EMC** : IEC 61000-4-4 (4 kV surge), IEC 61000-4-5 (2 kV).  
- **Alimentation** : 9–16 V bus bord.

## 6. Scénarios de test approfondis  
### 6.1 Validation de la précision des rails  
- Appliquer charges de 0, 1, 3, 5 A sur chaque rail.  
- Mesurer U(t), I(t) à 10 kHz.  
- Critère : respect des tolérances en continu.

### 6.2 Test de commutation rapide  
- Simuler basculement de charge de 5 V à 12 V (0→5 A instantané).  
- Chronométrer Δt entre bascule des MOSFETs et stabilisation de la tension.  
- Critère : < 100 µs, overshoot < 5 %.

### 6.3 Overcurrent et protection thermique  
- Régler seuil à 3 A, augmenter courant jusqu’à 6 A.  
- Mesurer temps de coupure et afficher event.  
- Critère : coupure < 50 µs, validité du log.

### 6.4 Test endurance flash  
- Générer 20 000 events, vérifier intégrité du ring buffer.  
- Effacer et relire log.  
- Critère : aucun event perdu, CRC ok.

### 6.5 Surveillance température  
- Augmenter T interne jusqu’à 90 °C en chambre.  
- Vérifier alerte et variation PWM pour réduire charge.  
- Critère : alerte émise < 100 ms après seuil.

## 7. Journal des résultats  
| Date       | Test                       | Conditions             | Résultat | Détails                        |
|------------|----------------------------|------------------------|----------|--------------------------------|
| 2025-06-08 | Précision rails            | 0–5 A                  | OK       | Écarts max 1,5 %               |
| 2025-06-12 | Commutation 5→12 V         | 5 A                    | OK       | Temps 85 µs, overshoot 3 %      |
| 2025-06-15 | Overcurrent (3 A seuil)    | Montée à 6 A           | OK       | Coupure 40 µs, log OK          |
| 2025-06-18 | Endurance flash            | 20 000 events          | OK       | Pas de corruption, CRC valide  |
| 2025-06-20 | Température 90 °C          | Chamber test           | OK       | Alerte en 80 ms                |

## 8. Maintenance et diagnostics  
- **Calibration des sense resistors** : tous les 6 mois, vérification ±1 %.  
- **Test EMC** : après toute modification du câblage.  
- **Mise à jour threshold** : via CLI SPI, versionné.  
- **Procédure de récupération** : clear log, reset hardware, re-test complet.
