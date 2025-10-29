"""
Routeur pour les endpoints de statistiques et informations

Ce module contient tous les endpoints liés aux statistiques
d'utilisation et aux informations du service.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models import StatisticsResponse, ServiceInfo
from app.services.kafka_service import KafkaManager
from app.services.sensor_simulator import SensorSimulator


logger = logging.getLogger(__name__)


def create_stats_router(
    kafka_manager: KafkaManager,
    sensor_simulator: SensorSimulator,
    statistics: dict,
    service_config: dict
) -> APIRouter:
    """
    Crée et configure le routeur des statistiques avec les dépendances injectées.
    
    Args:
        kafka_manager: Instance du gestionnaire Kafka
        sensor_simulator: Instance du simulateur de capteurs
        statistics: Dictionnaire des statistiques globales
        service_config: Configuration du service
    
    Returns:
        Routeur configuré pour les endpoints de statistiques
    """
    
    router = APIRouter(prefix="/api", tags=["Statistics"])
    
    @router.get(
        "/statistics",
        response_model=StatisticsResponse,
        summary="Obtenir les statistiques d'utilisation",
        description="Retourne les statistiques cumulatives d'utilisation du producteur IoT"
    )
    async def get_statistics() -> StatisticsResponse:
        """
        Retourne les statistiques d'utilisation du service.
        
        Inclut le nombre total d'événements publiés, de capteurs déclenchés,
        et les informations sur la configuration Kafka.
        
        Returns:
            Statistiques complètes du service
        """
        try:
            kafka_status = kafka_manager.get_connection_status()
            
            return StatisticsResponse(
                total_events_published=statistics['total_events_published'],
                total_sensors_triggered=statistics['total_sensors_triggered'],
                kafka_brokers=kafka_status.get('bootstrap_servers', []),
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve statistics: {str(e)}"
            )
    
    @router.delete(
        "/statistics/reset",
        summary="Réinitialiser les statistiques",
        description="Remet à zéro tous les compteurs de statistiques"
    )
    async def reset_statistics():
        """
        Remet à zéro les compteurs de statistiques.
        
        Utile pour les tests ou pour repartir à zéro après maintenance.
        
        Returns:
            Confirmation de la réinitialisation
        """
        try:
            old_events = statistics['total_events_published']
            old_sensors = statistics['total_sensors_triggered']
            
            statistics['total_events_published'] = 0
            statistics['total_sensors_triggered'] = 0
            
            logger.info(
                f"Statistics reset - Previous: {old_events} events, "
                f"{old_sensors} sensors triggered"
            )
            
            return {
                "status": "success",
                "message": "Statistics successfully reset",
                "previous_stats": {
                    "total_events_published": old_events,
                    "total_sensors_triggered": old_sensors
                },
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            logger.error(f"Error resetting statistics: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reset statistics: {str(e)}"
            )
    
    @router.get(
        "/info",
        response_model=ServiceInfo,
        summary="Informations détaillées du service",
        description="Retourne les informations complètes du service, sa configuration et son état"
    )
    async def service_info() -> ServiceInfo:
        """
        Retourne les informations complètes du service.
        
        Inclut la version, la description, la configuration Kafka,
        et les statistiques actuelles.
        
        Returns:
            Informations détaillées du service
        """
        try:
            kafka_status = kafka_manager.get_connection_status()
            
            kafka_info = {
                "brokers": kafka_status.get('bootstrap_servers', []),
                "sensor_topic": service_config.get('sensor_topic', 'sensors'),
                "alert_topic": service_config.get('alert_topic', 'alerts'),
                "connected": kafka_status.get('connected', False),
                "client_id": kafka_status.get('client_id', 'unknown')
            }
            
            stats_info = {
                "total_events_published": statistics['total_events_published'],
                "total_sensors_triggered": statistics['total_sensors_triggered'],
                "simulator_stats": sensor_simulator.get_statistics()
            }
            
            return ServiceInfo(
                service_name=service_config.get('name', 'IoT Sensor Producer'),
                version=service_config.get('version', '2.0.0'),
                description=service_config.get('description', 'Produces realistic sensor data to Kafka topics'),
                kafka=kafka_info,
                statistics=stats_info,
                timestamp=datetime.utcnow().isoformat() + 'Z'
            )
        except Exception as e:
            logger.error(f"Error getting service info: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve service info: {str(e)}"
            )
    
    @router.get(
        "/simulator/config",
        summary="Configuration du simulateur",
        description="Retourne la configuration actuelle du simulateur de capteurs"
    )
    async def get_simulator_config():
        """
        Retourne la configuration du simulateur de capteurs.
        
        Inclut les plages normales de valeurs, les seuils d'alertes,
        et les localisations disponibles.
        
        Returns:
            Configuration complète du simulateur
        """
        try:
            config = sensor_simulator.get_statistics()
            return {
                "status": "success",
                "simulator_configuration": config,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
        except Exception as e:
            logger.error(f"Error getting simulator config: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve simulator configuration: {str(e)}"
            )
    
    return router


def create_info_router(service_config: dict) -> APIRouter:
    """
    Crée le routeur pour les endpoints d'information générale.
    
    Args:
        service_config: Configuration du service
    
    Returns:
        Routeur pour les endpoints d'information
    """
    
    router = APIRouter(tags=["Info"])
    
    @router.get(
        "/",
        summary="Page d'accueil du service",
        description="Point d'entrée principal avec liens vers la documentation et les endpoints"
    )
    async def root():
        """
        Page d'accueil avec informations de base et liens utiles.
        
        Fournit une vue d'ensemble rapide du service et des liens
        vers la documentation interactive.
        
        Returns:
            Informations de base et liens de navigation
        """
        return {
            "service": service_config.get('name', 'IoT Sensor Producer'),
            "version": service_config.get('version', '2.0.0'),
            "status": "running",
            "description": "Système de simulation de capteurs IoT pour bâtiment intelligent",
            "features": [
                "Simulation de données de capteurs réalistes",
                "Détection d'anomalies en temps réel",
                "Publication vers Kafka",
                "API REST complète",
                "Monitoring et statistiques"
            ],
            "documentation": {
                "interactive_docs": "/docs",
                "redoc": "/redoc",
                "openapi_spec": "/openapi.json"
            },
            "quick_links": {
                "health_check": "/health",
                "trigger_sensors": "POST /api/sensors/trigger?count=5",
                "trigger_custom": "POST /api/sensors/trigger-single?sensor_id=test&temperature=25",
                "simulate_anomaly": "GET /api/sensors/simulate-anomaly?anomaly_type=high_temperature",
                "statistics": "GET /api/statistics",
                "service_info": "GET /api/info"
            },
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    
    return router