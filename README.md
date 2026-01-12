# 🏍️ BikerSentinel

[![GitHub Release](https://img.shields.io/github/v/release/werkey/bikersentinel?style=flat-square)](https://github.com/werkey/bikersentinel/releases)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange?style=flat-square)](https://hacs.xyz)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](https://www.python.org/)
[![Tests](https://github.com/werkey/bikersentinel/actions/workflows/tests.yml/badge.svg?style=flat-square)](https://github.com/werkey/bikersentinel/actions)

BikerSentinel is a data analysis engine for **Home Assistant** dedicated to motorcycle riding conditions. It combines the rider's physical parameters, machine characteristics, and meteorological data to generate a **"Biker Score"** (0-10) and safety indicators.

---

## ☕ Support

Love BikerSentinel? Consider buying me a coffee!

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFD700?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/werkey)

---

## 📋 Technical Specifications

### 1. Input Parameters (Rider & Machine Configuration)
* **Morphology (SCx)** : Frontal surface area calculation via **height (cm)** and **weight (kg)** for thermal exchange analysis.
* **Thermal Sensitivity** : Cold sensitivity slider (1-5) adjusting comfort thresholds.
* **Equipment (3 levels)** : Standard, Winter, or Heated (comfort index modulator).
* **Machine Type** : Roadster, Sportive, GT, Trail, Custom (aerodynamic protection impact).
* **Displacement** : Specific mode **125cc** (wind and average speed threshold adjustment).
* **Riding Context** : Urban, Road, or Highway (average riding speed for windchill calculation).

### 2. Calculation Algorithm (3-Layer Analysis)
1. **Security Layer (Veto)** : Immediate score block to **0/10** if :
   - Black ice risk (Ground temperature + Humidity).
   - Violent wind (Gusts > 85 km/h).
   - Severe phenomena (Lightning, Hail, Snow).
2. **Dynamic Thermal Comfort Layer** : **Windchill** calculation combining weather wind and trip speed (Urban/Road/Highway), weighted by SCx and equipment.
3. **Road Risk Layer** : Precipitation history analysis (24h) to detect "slippery roads" or aquaplaning risk.

### 3. Embedded Intelligence & Notifications
* **Lighting Management** : Automatic visibility malus (Night Mode) and glare alert (**Solar Blindness**) per sun azimuth.
* **Commute Alert** : Predictive notification before work departure time to anticipate return trip.
* **Gear Advisor** : Equipment suggestion (lining, gloves, visor) before departure.

### 4. Generated Entities
* **Score (0-10)** : The final numeric value.
* **Status** : Comfort label (Optimal, Critical, etc.).
* **Reasoning** : Textual detail of calculations (ex: "Strong lateral wind, Temp below 5°C, Rain risk detected").

---

## 📊 Implemented Features (Phase 1 + Phase 2 partial)

See [VERIFICATION_FEATURES.md](VERIFICATION_FEATURES.md) for detailed analysis of all implemented features with code line references.

---

## 🚀 Development Roadmap

**Version** : 1.2.0 | **Status** : ✅ Production-ready

### ✅ Phase 1 : Foundations (Version 1.0.0)
- [x] Custom component architecture.
- [x] Configuration form (Config Flow) & `Score`/`Status` entities.

### ✅ Phase 2 : Algorithm Development (Partially completed)
- [x] **Stability Malus** : Lateral wind impact per machine type.
- [x] **Sensitivity/Equipment Integration** : New calculation options in the engine.
- [x] **Riding Context** : Dynamic speed adjustable by user (urban/road/highway).
- [ ] **Night Mode & Azimuth** : Visibility calculation based on solar position.
- [ ] **Precipitation History** : 24h correlation with road state.

### 🌟 Phase 3 : Advanced Features ("Apotheosis")
- [ ] **Maintenance** : Chain lubrication reminders after rain and predictive maintenance tracking.
- [ ] **Machine Learning** : Auto-adjustment of cold sensitivity per real riding data.
- [ ] **Cost Analysis** : Financial comparison Motorcycle vs Car per trip.
- [ ] **Roadtrip Checklist** : Dynamic preparation assistant.

---

## 🛠️ Installation

### Prerequisites
- Home Assistant 2024.1 or later
- Temperature, wind, and rain sensors available in HA

### Steps
1. Copy the `bikersentinel` folder to `/config/custom_components/`
   ```bash
   cp -r bikersentinel /config/custom_components/
   ```
2. Restart Home Assistant
3. Go to **Settings → Devices and Services → Integrations**
4. Click **"Create Integration"** and select **BikerSentinel**
5. Configure :
   - Select your sensors (Temp, Wind, Rain)
   - Optional : Global weather entity
   - Personal parameters (Height, Weight, Cold Sensitivity, Motorcycle Type, Equipment)

### Multi-Instance
You can create multiple configurations (ex: "My Bike", "Wife's Bike", "Scooter 125"). Each instance generates its 3 sensors.

---

## 🔧 Customization

### Modify Coefficients
Edit `bikersentinel/const.py` :
- `PROTECTION_COEFS` : Aerodynamic coefficients per motorcycle type
- `EQUIPMENT_COEFS` : Cold reduction per equipment level
- Restart Home Assistant

### Adjust Malus Thresholds
Modify in `bikersentinel/sensor.py` (class `BikerSentinelScore`) :
- Temperature thresholds for windchill
- Wind thresholds for stability
- Malus values (-3, -1.5, etc.)

---

## 🤝 Contributing

We welcome contributions! Whether it's bug fixes, new features, or documentation improvements, please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Links
- 📋 [Development Setup](CONTRIBUTING.md#development-setup)
- 🐛 [Open an Issue](https://github.com/werkey/bikersentinel/issues)
- 🚀 [Create a Pull Request](https://github.com/werkey/bikersentinel/pulls)

---

## 📝 License

BikerSentinel is licensed under the [MIT License](LICENSE).

---

## 🎯 Roadmap

See [VERIFICATION_FEATURES.md](VERIFICATION_FEATURES.md) for detailed feature matrix and Phase 2+ planned features.

---

**Made with ❤️ for motorcycle riders worldwide.**
