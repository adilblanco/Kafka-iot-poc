"""
Routeur pour les endpoints de gestion des capteurs

Ce module contient tous les endpoints liés à la simulation
et au déclenchement des capteurs IoT.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from models import SensorData, TriggerResponse
from services.kafka_service import KafkaManager
from services.sensor_simulator import SensorSimulator


logger = logging.getLogger(__name__)

# Configuration des topics
SENSOR_TOPIC = "sensors"
ALERT_TOPIC = "alerts"


def create_sensors_router(
    kafka_manager: KafkaManager, 
    sensor_simulator: SensorSimulator,
    statistics: dict
) -> APIRouter:
    """
    Crée et configure le routeur des capteurs avec les dépendances injectées.
    
    Args:
        kafka_manager: Instance du gestionnaire Kafka
        sensor_simulator: Instance du simulateur de capteurs
        statistics: Dictionnaire des statistiques globales
    
    Returns:
        Routeur configuré pour les endpoints de capteurs
    """
    
    router = APIRouter(prefix="/api/sensors", tags=["Sensors"])
    
    @router.post(
        "/trigger",
        response_model=TriggerResponse,
        summary="Déclencher des lectures de capteurs",
        description="Déclenche la publication de N lectures de capteurs sur Kafka avec données générées automatiquement"
    )
    async def trigger_sensors(
        count: int = Query(
            default=3,
            ge=1,
            le=100,
            description="Nombre de capteurs à simuler (1-100)"
        )
    ) -> TriggerResponse:
        """
        Déclenche la publication de plusieurs lectures de capteurs.
        
        Génère des données réalistes pour un nombre spécifié de capteurs
        et les publie sur le topic Kafka 'sensors'.
        
        **Exemple d'utilisation:**
        ```
        POST /api/sensors/trigger?count=5
        ```
        
        **Réponse type:**
        ```json
        {
          "status": "success",
          "sensors_triggered": 5,
          "events_published": 5,
          "topic": "sensors",
          "timestamp": "2025-10-29T14:30:00.123456Z",
          "message": "Successfully published 5/5 sensor events"
        }
        ```
        
        Args:
            count: Nombre de capteurs à simuler
            
        Returns:
            Réponse avec les détails de l'opération
            
        Raises:
            HTTPException: Si Kafka n'est pas disponible ou erreur de publication
        """
        
        # Vérification de la connexion Kafka
        if not kafka_manager.is_connected:
            raise HTTPException(
                status_code=503,
                detail="Kafka connection unavailable. Check service health."
            )
        
        try:
            # Génération du lot de données
            logger.info(f"Generating {count} sensor readings...")
            batch = sensor_simulator.generate_batch(count)
            
            # Publication sur Kafka
            published_count = 0
            alerts_generated = 0
            
            for sensor_data in batch:
                # Conversion en dictionnaire pour Kafka
                data_dict = sensor_data.dict()
                
                # Publication des données du capteur
                if kafka_manager.publish_message(SENSOR_TOPIC, data_dict):
                    published_count += 1
                    statistics['total_events_published'] += 1
                    
                    # Détection d'anomalies et génération d'alertes
                    alerts = sensor_simulator.detect_anomalies(sensor_data)
                    for alert in alerts:
                        if kafka_manager.publish_message(ALERT_TOPIC, alert.dict()):
                            alerts_generated += 1
                            logger.info(f"Alert generated: {alert.alert_type} for {alert.sensor_id}")
            
            # Mise à jour des statistiques
            statistics['total_sensors_triggered'] += count
            
            # Création de la réponse
            success_message = f"Successfully published {published_count}/{count} sensor events"
            if alerts_generated > 0:
                success_message += f" and {alerts_generated} alerts"
            
            logger.info(f"Batch operation completed: {success_message}")
            
            return TriggerResponse(
                status="success",
                sensors_triggered=count,
                events_published=published_count,
                topic=SENSOR_TOPIC,
                timestamp=datetime.utcnow().isoformat() + 'Z',
                message=success_message
            )
        
        except Exception as e:
            error_msg = f"Failed to trigger sensors: {str(e)}"
            logger.error(f"{error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
    
    @router.post(
        "/trigger-single",
        response_model=TriggerResponse,
        summary="Déclencher une lecture unique avec paramètres personnalisés",
        description="Déclenche la publication d'UNE lecture de capteur avec des paramètres spécifiques"
    )
    async def trigger_single_sensor(
        sensor_id: str = Query(
            default="sensor_custom",
            description="Identifiant unique du capteur"
        ),
        temperature: float = Query(
            default=22.5,
            ge=15,
            le=35,
            description="Température en Celsius (15-35°C)"
        ),
        humidity: float = Query(
            default=55,
            ge=20,
            le=95,
            description="Humidité relative en % (20-95%)"
        ),
        pressure: Optional[float] = Query(
            default=None,
            ge=980,
            le=1040,
            description="Pression atmosphérique en hPa (optionnel, 980-1040)"
        )
    ) -> TriggerResponse:
        """
        Déclenche la publication d'une lecture de capteur personnalisée.
        
        Utile pour tester des scénarios spécifiques ou simuler des conditions
        particulières (ex: température élevée pour tester les alertes).
        
        **Exemple d'utilisation:**
        ```
        POST /api/sensors/trigger-single?sensor_id=sensor_test&temperature=28.5&humidity=70
        ```
        
        Args:
            sensor_id: Identifiant du capteur
            temperature: Température à simuler
            humidity: Humidité à simuler  
            pressure: Pression (optionnel, généré automatiquement si non fourni)
            
        Returns:
            Réponse avec les détails de l'opération
            
        Raises:
            HTTPException: Si Kafka n'est pas disponible ou erreur de publication
        """
        
        if not kafka_manager.is_connected:
            raise HTTPException(
                status_code=503,
                detail="Kafka connection unavailable"
            )
        
        try:
            # Génération des données personnalisées
            sensor_data = sensor_simulator.generate_custom_sensor_data(
                sensor_id=sensor_id,
                temperature=temperature,
                humidity=humidity,
                pressure=pressure
            )
            
            # Publication sur Kafka
            if kafka_manager.publish_message(SENSOR_TOPIC, sensor_data.dict()):
                statistics['total_events_published'] += 1
                statistics['total_sensors_triggered'] += 1
                
                # Détection et publication d'alertes
                alerts = sensor_simulator.detect_anomalies(sensor_data)
                alerts_count = 0
                for alert in alerts:
                    if kafka_manager.publish_message(ALERT_TOPIC, alert.dict()):
                        alerts_count += 1
                        logger.info(f"Alert generated: {alert.alert_type} for {alert.sensor_id}")
                
                success_message = f"Custom sensor event published"
                if alerts_count > 0:
                    success_message += f" with {alerts_count} alerts"
                
                logger.info(
                    f"Custom sensor published: {sensor_id} | "
                    f"temp={temperature}°C | humidity={humidity}%"
                )
                
                return TriggerResponse(
                    status="success",
                    sensors_triggered=1,
                    events_published=1,
                    topic=SENSOR_TOPIC,
                    timestamp=datetime.utcnow().isoformat() + 'Z',
                    message=success_message
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to publish sensor data to Kafka"
                )
        
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Error in single sensor trigger: {str(e)}"
            logger.error(f"{error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
    
    @router.get(
        "/simulate-anomaly",
        response_model=TriggerResponse,
        summary="Simuler une anomalie spécifique",
        description="Génère délibérément des données anormales pour tester le système d'alertes"
    )
    async def simulate_anomaly(
        anomaly_type: str = Query(
            default="high_temperature",
            description="Type d'anomalie à simuler",
            regex="^(high_temperature|low_temperature|high_humidity|low_humidity|low_battery)$"
        ),
        sensor_id: str = Query(
            default="sensor_anomaly_test",
            description="ID du capteur pour l'anomalie"
        )
    ):
        """
        Simule une anomalie spécifique pour tester le système d'alertes.
        
        Types d'anomalies disponibles:
        - high_temperature: Température > 26°C
        - low_temperature: Température < 18°C  
        - high_humidity: Humidité > 80%
        - low_humidity: Humidité < 30%
        - low_battery: Batterie < 20%
        
        Args:
            anomaly_type: Type d'anomalie à simuler
            sensor_id: Identifiant du capteur
            
        Returns:
            Réponse avec les détails de l'anomalie simulée
        """
        
        if not kafka_manager.is_connected:
            raise HTTPException(status_code=503, detail="Kafka unavailable")
        
        try:
            # Paramètres d'anomalie
            anomaly_params = {
                "high_temperature": {"temperature": 29.0, "humidity": 45.0},
                "low_temperature": {"temperature": 16.0, "humidity": 75.0},
                "high_humidity": {"temperature": 24.0, "humidity": 85.0},
                "low_humidity": {"temperature": 25.0, "humidity": 25.0},
                "low_battery": {"temperature": 22.0, "humidity": 55.0}
            }
            
            params = anomaly_params[anomaly_type]
            
            # Génération avec paramètres d'anomalie
            sensor_data = sensor_simulator.generate_custom_sensor_data(
                sensor_id=sensor_id,
                temperature=params["temperature"],
                humidity=params["humidity"],
                battery_level=0.15 if anomaly_type == "low_battery" else None
            )
            
            # Publication
            if kafka_manager.publish_message(SENSOR_TOPIC, sensor_data.dict()):
                # Détection et publication d'alertes
                alerts = sensor_simulator.detect_anomalies(sensor_data)
                alerts_published = 0
                
                for alert in alerts:
                    if kafka_manager.publish_message(ALERT_TOPIC, alert.dict()):
                        alerts_published += 1
                
                statistics['total_events_published'] += 1
                statistics['total_sensors_triggered'] += 1
                
                return TriggerResponse(
                    status="success",
                    sensors_triggered=1,
                    events_published=1,
                    topic=SENSOR_TOPIC,
                    timestamp=datetime.utcnow().isoformat() + 'Z',
                    message=f"Anomaly '{anomaly_type}' simulated with {alerts_published} alerts generated"
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to publish anomaly data")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error simulating anomaly: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router