"""
Modèles de données pour le système IoT

Ce module contient tous les modèles Pydantic utilisés pour la validation
et la sérialisation des données dans le système de monitoring IoT.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SensorData(BaseModel):
    """
    Modèle représentant les données d'un capteur environnemental.
    
    Ce modèle définit la structure des données collectées par les capteurs
    du bâtiment intelligent (température, humidité, pression, etc.).
    """
    sensor_id: str = Field(description="Identifiant unique du capteur")
    timestamp: str = Field(description="Timestamp ISO 8601")
    temperature: float = Field(description="Température en Celsius", ge=15, le=35)
    humidity: float = Field(description="Humidité relative en %", ge=20, le=95)
    pressure: float = Field(description="Pression atmosphérique en hPa")
    battery_level: float = Field(description="Niveau batterie (0-1)", ge=0, le=1)

    class Config:
        """Configuration du modèle"""
        schema_extra = {
            "example": {
                "sensor_id": "sensor_001",
                "timestamp": "2025-10-29T14:30:00.123456Z",
                "temperature": 22.5,
                "humidity": 55.0,
                "pressure": 1013.25,
                "battery_level": 0.85
            }
        }


class TriggerResponse(BaseModel):
    """
    Réponse retournée lors du déclenchement d'événements de capteurs.
    
    Utilisé pour informer l'utilisateur du résultat d'une opération
    de déclenchement de capteurs.
    """
    status: str = Field(description="Statut de l'opération (success/error)")
    sensors_triggered: int = Field(description="Nombre de capteurs déclenchés")
    events_published: int = Field(description="Nombre d'événements publiés")
    topic: str = Field(description="Topic Kafka utilisé")
    timestamp: str = Field(description="Timestamp de l'opération")
    message: str = Field(default="", description="Message descriptif optionnel")


class HealthResponse(BaseModel):
    """
    Réponse du health check du service.
    
    Fournit des informations sur l'état de santé du service
    et de ses dépendances (Kafka).
    """
    status: str = Field(description="État général (healthy/unhealthy)")
    service: str = Field(description="Nom du service")
    kafka_connected: bool = Field(description="État de la connexion Kafka")
    topics: List[str] = Field(default=[], description="Topics Kafka disponibles")


class StatisticsResponse(BaseModel):
    """
    Statistiques d'utilisation du service.
    
    Contient les métriques cumulatives d'utilisation du producteur IoT.
    """
    total_events_published: int = Field(description="Total d'événements publiés")
    total_sensors_triggered: int = Field(description="Total de capteurs déclenchés")
    kafka_brokers: List[str] = Field(description="Liste des brokers Kafka")
    timestamp: str = Field(description="Timestamp des statistiques")


class SensorAlert(BaseModel):
    """
    Modèle pour les alertes générées par le système de monitoring.
    
    Représente une alerte déclenchée lorsqu'une anomalie est détectée
    dans les données d'un capteur.
    """
    alert_id: str = Field(description="Identifiant unique de l'alerte")
    sensor_id: str = Field(description="Capteur concerné")
    alert_type: str = Field(description="Type d'alerte (temperature, humidity, etc.)")
    severity: str = Field(description="Sévérité (low, medium, high, critical)")
    value: float = Field(description="Valeur qui a déclenché l'alerte")
    threshold: float = Field(description="Seuil dépassé")
    message: str = Field(description="Message descriptif de l'alerte")
    timestamp: str = Field(description="Timestamp de l'alerte")

    class Config:
        """Configuration du modèle"""
        schema_extra = {
            "example": {
                "alert_id": "alert_001",
                "sensor_id": "sensor_001",
                "alert_type": "temperature",
                "severity": "high",
                "value": 28.5,
                "threshold": 26.0,
                "message": "Température élevée détectée",
                "timestamp": "2025-10-29T14:30:00.123456Z"
            }
        }


class ServiceInfo(BaseModel):
    """
    Informations complètes du service.
    
    Modèle pour l'endpoint d'information du service.
    """
    service_name: str = Field(description="Nom du service")
    version: str = Field(description="Version du service")
    description: str = Field(description="Description du service")
    kafka: dict = Field(description="Configuration Kafka")
    statistics: dict = Field(description="Statistiques actuelles")
    timestamp: str = Field(description="Timestamp des informations")