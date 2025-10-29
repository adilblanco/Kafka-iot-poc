# Système IoT de Monitoring Environnemental - Version Modulaire

## Vue d'ensemble

Cette version refactorisée de votre preuve de concept IoT propose une architecture modulaire, propre et maintenable pour un système de monitoring de capteurs environnementaux dans un bâtiment intelligent.

## Architecture

### Structure du projet

```
app/
├── __init__.py
├── models/                      # Modèles de données Pydantic
│   └── __init__.py             # SensorData, TriggerResponse, etc.
├── services/                    # Logique métier
│   ├── __init__.py
│   ├── kafka_service.py        # Gestion Kafka
│   └── sensor_simulator.py     # Simulation de capteurs
├── api/                        # Routeurs FastAPI
│   ├── __init__.py
│   ├── health.py              # Endpoints de santé
│   ├── sensors.py             # Endpoints capteurs
│   └── stats.py               # Endpoints statistiques
└── core/                       # Configuration et utilitaires
    ├── __init__.py
    └── config.py              # Configuration centralisée
main.py                        # Point d'entrée principal
```

## Améliorations apportées

### 1. **Séparation des responsabilités**
- **Modèles** : Définition des structures de données
- **Services** : Logique métier (Kafka, simulation)
- **API** : Routeurs et endpoints
- **Core** : Configuration et utilitaires

### 2. **Configuration centralisée**
- Variables d'environnement
- Configuration par défaut
- Validation de config
- Support debug/production

### 3. **Gestion d'erreurs améliorée**
- Gestionnaires d'exception globaux
- Logging structuré
- Messages d'erreur informatifs

### 4. **Extensibilité**
- Ajout facile de nouveaux types de capteurs
- Extension des seuils d'alerte
- Nouveaux endpoints sans refactoring

### 5. **Monitoring et observabilité**
- Health checks détaillés
- Statistiques complètes
- Logs structurés

## Utilisation

### Démarrage rapide

```bash
# Installation des dépendances
pip install -r requirements.txt

# Démarrage en mode développement
python main.py

# Ou avec uvicorn
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

### Configuration via variables d'environnement

```bash
# Service
export SERVICE_NAME="IoT Sensor Producer"
export SERVICE_VERSION="2.0.0"
export HOST="0.0.0.0"
export PORT="5000"
export LOG_LEVEL="INFO"
export DEBUG="false"

# Kafka
export KAFKA_BOOTSTRAP_SERVERS="kafka:29092,kafka2:29093"
export KAFKA_SENSOR_TOPIC="sensors"
export KAFKA_ALERT_TOPIC="alerts"
export KAFKA_CLIENT_ID="iot_producer"
```

## Endpoints principaux

### Health & Monitoring
- `GET /health` - Santé du service
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe
- `GET /health/kafka` - État Kafka détaillé

### Capteurs
- `POST /api/sensors/trigger?count=5` - Déclencher N capteurs
- `POST /api/sensors/trigger-single` - Capteur personnalisé
- `GET /api/sensors/simulate-anomaly` - Simuler une anomalie

### Statistiques
- `GET /api/statistics` - Statistiques d'utilisation
- `DELETE /api/statistics/reset` - Reset des compteurs
- `GET /api/info` - Informations détaillées

## Fonctionnalités avancées

### Détection d'anomalies
Le système détecte automatiquement :
- Températures anormales (< 18°C ou > 26°C)
- Humidité excessive (> 80%) ou insuffisante (< 30%)
- Pressions atypiques
- Batterie faible (< 20%)

### Types d'anomalies simulables
- `high_temperature` : Température > 26°C
- `low_temperature` : Température < 18°C
- `high_humidity` : Humidité > 80%
- `low_humidity` : Humidité < 30%
- `low_battery` : Batterie < 20%

### Localisation réaliste
Le simulateur utilise des localisations prédéfinies :
- Bureaux (101, 102, etc.)
- Salles de réunion
- Espaces communs
- Zones techniques

## Sécurité et production

### Bonnes pratiques implémentées
- Validation stricte des inputs
- Gestion d'erreurs robuste
- Logging sans données sensibles
- Configuration par environnement

### Pour la production
- Configurer les CORS appropriés
- Utiliser des secrets pour Kafka
- Activer l'authentification si nécessaire
- Monitoring avec Prometheus/Grafana

## Tests et développement

### Mode debug
```bash
export DEBUG="true"
python main.py
```

### Testing des anomalies
```bash
# Température élevée
curl "http://localhost:5000/api/sensors/simulate-anomaly?anomaly_type=high_temperature"

# Capteur personnalisé
curl -X POST "http://localhost:5000/api/sensors/trigger-single?sensor_id=test&temperature=30&humidity=85"
```

## Monitoring

### Métriques disponibles
- Nombre total d'événements publiés
- Nombre de capteurs déclenchés
- État des connexions Kafka
- Alertes générées par type

### Health checks
- `/health` : Santé générale
- `/health/ready` : Prêt à traiter
- `/health/live` : Service vivant
- `/health/kafka` : Connectivité Kafka

## Évolution et maintenance

### Ajout d'un nouveau type de capteur
1. Étendre `SensorData` dans `models/`
2. Ajouter la logique dans `SensorSimulator`
3. Créer les seuils d'alerte appropriés

### Ajout d'un endpoint
1. Créer un nouveau routeur dans `api/`
2. L'inclure dans `main.py`
3. Tester et documenter

Cette architecture modulaire facilite grandement la maintenance, les tests et l'évolution de votre système IoT !