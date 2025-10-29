"""
Routeur pour les endpoints de santé du service

Ce module contient tous les endpoints liés à la surveillance
de la santé du service et de ses dépendances.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from models import HealthResponse
from services.kafka_service import KafkaManager, KafkaHealthChecker


logger = logging.getLogger(__name__)


def create_health_router(kafka_manager: KafkaManager) -> APIRouter:
    """
    Crée et configure le routeur de santé avec les dépendances injectées.
    
    Args:
        kafka_manager: Instance du gestionnaire Kafka
    
    Returns:
        Routeur configuré pour les endpoints de santé
    """
    
    # Création du routeur pour les endpoints de santé
    router = APIRouter(prefix="/health", tags=["Health"])
    
    @router.get(
        "",
        response_model=HealthResponse,
        summary="Vérifier la santé du service",
        description="Endpoint principal de health check pour vérifier l'état du service et de ses dépendances"
    )
    async def health_check():
        """
        Vérifie l'état de santé général du service.
        
        Retourne l'état du service et de ses connexions (Kafka).
        Utilisé par les orchestrateurs pour monitorer le service.
        """
        try:
            kafka_status = kafka_manager.get_connection_status()
            
            return HealthResponse(
                status="healthy" if kafka_status["connected"] else "unhealthy",
                service="iot_sensor_producer",
                kafka_connected=kafka_status["connected"],
                topics=["sensors", "alerts"]  # Topics configurés
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return HealthResponse(
                status="unhealthy",
                service="iot_sensor_producer",
                kafka_connected=False,
                topics=[]
            )
    
    @router.get(
        "/ready",
        summary="Vérifier la disponibilité du service",
        description="Endpoint de readiness pour vérifier si le service est prêt à traiter les requêtes"
    )
    async def readiness_check():
        """
        Vérifie si le service est prêt à traiter les requêtes.
        
        Diffère du health check en vérifiant que toutes les dépendances
        critiques sont opérationnelles.
        """
        try:
            kafka_status = kafka_manager.get_connection_status()
            
            if not kafka_status["connected"]:
                raise HTTPException(
                    status_code=503,
                    detail="Service not ready: Kafka connection unavailable"
                )
            
            return {
                "status": "ready",
                "service": "iot_sensor_producer",
                "kafka_connected": True,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Readiness check failed: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Service not ready: {str(e)}"
            )
    
    @router.get(
        "/live",
        summary="Liveness probe",
        description="Endpoint simple pour vérifier que le service répond (liveness probe)"
    )
    async def liveness_check():
        """
        Probe de vivacité pour les orchestrateurs.
        
        Endpoint simple qui vérifie uniquement que le service répond.
        Ne vérifie pas les dépendances externes.
        """
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    
    @router.get(
        "/kafka",
        summary="État détaillé de Kafka",
        description="Informations détaillées sur la connexion et configuration Kafka"
    )
    async def kafka_health():
        """
        Retourne l'état détaillé de la connexion Kafka.
        
        Utile pour le debugging et le monitoring avancé.
        """
        try:
            kafka_status = kafka_manager.get_connection_status()
            
            # Test de connectivité supplémentaire
            connectivity_test = KafkaHealthChecker.check_connectivity(
                kafka_status["bootstrap_servers"],
                timeout=5
            )
            
            return {
                "kafka_manager_status": kafka_status,
                "connectivity_test": connectivity_test,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
            
        except Exception as e:
            logger.error(f"Kafka health check failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check Kafka health: {str(e)}"
            )
    
    return router