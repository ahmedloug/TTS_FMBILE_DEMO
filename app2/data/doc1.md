# doc01_temperature_sensor.md

## 1. Contexte et objectifs  
Le module **TempSense** est destiné à mesurer la température d’un fluide de refroidissement dans un process industriel continu. Il doit fournir une mesure fiable pour optimiser la régulation thermique et prévenir la surchauffe.  
- **Environnement** : rack étanche IP67, exposition à des variations rapides de –40 °C à +125 °C.  
- **Cadence** : collecte des mesures toutes les 100 ms pour alimentation d’un PID de régulation.  

## 2. Vue système et composants  
- **Thermistor NTC 10 kΩ** à coefficient B élevé pour linéarité.  
- **ADC 16 bits sigma-delta** intégré au microcontrôleur STM32L4.  
- **Microcontrôleur** : fréquence 80 MHz, algorithme de linéarisation par table LUT.  
- **Interface** : bus I²C à 400 kHz, opto-couplé pour isolation galvanique.  
- **Boîtier** : alliage aluminium à faible inertie thermique  

## 3. Architecture logicielle  
1. **Acquisition brute** : échantillonnage ADC, moyenne glissante sur 5 points.  
2. **Linéarisation** : conversion via table LUT calibrée en usine.  
3. **Filtrage** : filtre passe-bas numérique à fc = 5 Hz pour atténuer le bruit.  
4. **Communication** : écriture périodique sur registre I²C, gestion des erreurs (ACK/NACK).  
5. **Mode veille** : après 1 s sans requête, mise en sommeil profondeur, réveil par timer interne.  

## 4. Exigences fonctionnelles  
- **REQ-TS-001 :** Plage de mesure complète de –40 °C à +125 °C (linéaire ±0,2 °C).  
- **REQ-TS-002 :** Précision spectrale ±0,1 °C entre 0 °C et +85 °C, ±0,5 °C sur les extrêmes.  
- **REQ-TS-003 :** Taux d’échantillonnage minimum 10 Hz stable ±0,1 %.  
- **REQ-TS-004 :** Temps de montée T₉₀ (step change 25→85 °C) < 200 ms.  
- **REQ-TS-005 :** Consommation ≤ 1 mW en mode actif, ≤ 5 µW en veille.  
- **REQ-TS-006 :** Détecter et signaler une coupure de capteur (TC > 150 kΩ) en < 50 ms.  

## 5. Environnement et contraintes  
- **Vibrations** : supporte 5 g en choc sinusoïdal 10–500 Hz.  
- **EMC/EMI** : conforme IEC 61000-4-3 (3 V/m) et IEC 61000-4-6 (10 V).  
- **Chocs** : 1000 chocs de 50 g, 6 ms.  
- **Humidité** : fonctionnement 0–95 % HR sans condensation.  

## 6. Scénarios de test détaillés  
### 6.1 Calibration en bain étalon  
- Plages : –40, 0, +25, +85, +125 °C.  
- Méthode : étalon NIST, cinq répétitions par température.  
- Critère : erreur maximale ≤ 0,1 °C (0–85 °C), ≤ 0,5 °C aux extrêmes.  

### 6.2 Step change thermique  
- Procédure : transition rapide 25→85 °C via chambre climatique.  
- Mesure : acquisition à 1 kHz, calcul de T₉₀.  
- Critère : T₉₀ < 200 ms, sans overshoot > 5 %.  

### 6.3 Test I²C et robustesse  
- Chargement : 1 000 lectures consécutives à 400 kHz.  
- Indicateurs : taux d’échec de transmission, temps moyen de lecture.  
- Critère : erreurs < 0,01 %, temps < 5 ms/lecture.  

### 6.4 Vieillissement accéléré  
- Cycle thermique : –40→125 °C, 500 cycles, 1 cycle/min.  
- Vérification : post-test calibration, écart ≤ 0,2 °C.  

### 6.5 Test de coupure capteur  
- Augmenter résistance capteur de façon progressive.  
- Valider alerte < 50 ms et retour d’état I²C spécifique.  

## 7. Journal de suivi des tests  
| Date       | Test                         | Paramètres             | Résultat | Commentaires                 |
|------------|------------------------------|------------------------|----------|------------------------------|
| 2025-06-10 | Calibration – standard       | 5 températures         | OK       | Écarts max 0,08 °C           |
| 2025-06-12 | Step change 25→85 °C         | T₉₀ mesuré 175 ms      | OK       | Overshoot 3 %                |
| 2025-06-15 | I²C 400 kHz, 1000 lectures   | Erreurs 0,005 %        | OK       |                              |
| 2025-06-20 | Vieillissement 500 cycles    | Écart post-cal 0,15 °C | OK       |                              |
| 2025-06-25 | Coupure capteur simulée      | Alerte en 42 ms        | OK       |                              |

## 8. Maintenance et calibration  
- **Calibration périodique** : tous les 1 000 heures de fonctionnement.  
- **Vérification EMC** : annuelle ou après toute modification hardware.  
- **Mise à jour firmware** : via bootloader I²C, versioning sémantique.  
