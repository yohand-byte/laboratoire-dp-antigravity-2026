# 🚀 Laboratoire DP Antigravity 2026

Projet de génération automatisée de Déclarations Préalables (DP) pour installations solaires.

## 🎯 Vision

Automatiser à 100% la génération de DP conformes aux standards mairie, en éliminant les retouches manuelles.

## 📊 Roadmap

### Phase 1 : Planification ✅
- [x] Analyse des repos existants
- [x] Identification des points de friction
- [x] Création du plan d'implémentation

### Phase 2 : Infrastructure ✅
- [x] Migration HTML-CARTO sur Cloud Run
- [x] Nouveaux endpoints validation/rendu
- [x] Déploiement : https://html-carto-api-29459740400.europe-west1.run.app

### Phase 3 : Laboratoire 🔄
- [x] Création projet dp-generator-lab
- [x] Interface validation cartographique (Leaflet)
- [x] Intégration éditeur calepinage 2D/3D
- [ ] Test end-to-end
- [ ] Déploiement Cloud Run

### Phase 4 : Conformité
- [ ] Analyse PDF de référence
- [ ] Alignement rendu DP1-DP11
- [ ] Validation mairie

## 🏗️ Architecture

```
laboratoire-dp-antigravity-2026/
├── html-carto-api/          # API cartographique (Cloud Run)
│   ├── main.py              # FastAPI endpoints
│   ├── Dockerfile
│   └── deploy.sh
│
├── dp-generator-lab/        # Laboratoire principal
│   ├── main.py              # FastAPI app
│   ├── templates/           # HTML (Jinja2)
│   ├── modules/             # Python modules
│   │   ├── calepinage_editor.py
│   │   └── solar_3d_visualizer.py
│   └── assets/              # Images exemples
│
└── docs/                    # Documentation
    └── ROADMAP.md
```

## 🔗 Services déployés

| Service | URL | Status |
|---------|-----|--------|
| HTML-CARTO API | https://html-carto-api-29459740400.europe-west1.run.app | ✅ Live |
| DP Generator Lab | En cours de développement | 🔄 Dev |

## 🛠️ Stack technique

- **Backend** : FastAPI (Python 3.11)
- **Frontend** : Vanilla JS + Leaflet + Three.js
- **Cartes** : IGN GéoPF (WMS/WMTS)
- **PDF** : ReportLab
- **Cloud** : Google Cloud Run

## 📝 Changelog

### 2026-01-11
- ✅ HTML-CARTO API déployée sur Cloud Run
- ✅ Endpoints `/api/validate-location` et `/api/render-map` créés
- ✅ Laboratoire dp-generator-lab initialisé
- ✅ Interface validation carto avec Leaflet
- ✅ Intégration modules CALEPINAGE 3D REPLICA

## 👤 Auteur

Solaire Facile - Yohan Aboujdid
