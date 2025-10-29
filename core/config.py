"""
Configuration centralisée pour l'application IoT

Ce module gère toute la configuration de l'application,
y compris les variables d'environnement, les paramètres
Kafka, et les configurations par défaut.
"""

import os
import logging
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    """Configuration pour Kafka"""
    bootstrap_servers: List[str]
    sensor_topic: str
    alert_topic: str
    client_id: str
    acks: str = 'all'
    retries: int = 3
    linger_ms: int = 10
    compression_type: str = 'gzip'


@dataclass
class ServiceConfig:
    """Configuration générale du service"""
    name: str
    version: str
    description: str
    host: str
    port: int
    log_level: str
    debug: bool = False


@dataclass
class AppConfig:
    """Configuration complète de l'application"""
    service: ServiceConfig
    kafka: KafkaConfig


class ConfigManager:
    """
    Gestionnaire centralisé de configuration.
    
    Charge la configuration depuis les variables d'environnement
    avec des valeurs par défaut appropriées pour le développement.
    """
    
    def __init__(self):
        """Initialise le gestionnaire de configuration."""
        self._setup_logging()
        self.config = self._load_config()
    
    def _setup_logging(self):
        """Configure le logging pour le gestionnaire."""
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> AppConfig:
        """
        Charge la configuration depuis les variables d'environnement.
        
        Returns:
            Configuration complète de l'application
        """
        # Configuration du service
        service_config = ServiceConfig(
            name=os.getenv('SERVICE_NAME', 'IoT Sensor Producer'),
            version=os.getenv('SERVICE_VERSION', '2.0.0'),
            description=os.getenv(
                'SERVICE_DESCRIPTION', 
                'Système de simulation de capteurs IoT pour bâtiment intelligent'
            ),
            host=os.getenv('HOST', '0.0.0.0'),
            port=int(os.getenv('PORT', '5001')),
            log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        )
        
        # Configuration Kafka
        bootstrap_servers_str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '127.0.0.1:9092')
        bootstrap_servers = [server.strip() for server in bootstrap_servers_str.split(',')]
        
        kafka_config = KafkaConfig(
            bootstrap_servers=bootstrap_servers,
            sensor_topic=os.getenv('KAFKA_SENSOR_TOPIC', 'sensors'),
            alert_topic=os.getenv('KAFKA_ALERT_TOPIC', 'alerts'),
            client_id=os.getenv('KAFKA_CLIENT_ID', 'iot_producer'),
            acks=os.getenv('KAFKA_ACKS', 'all'),
            retries=int(os.getenv('KAFKA_RETRIES', '3')),
            linger_ms=int(os.getenv('KAFKA_LINGER_MS', '10')),
            compression_type=os.getenv('KAFKA_COMPRESSION_TYPE', 'gzip')
        )
        
        self.logger.info("Configuration loaded successfully")
        self.logger.info(f"Service: {service_config.name} v{service_config.version}")
        self.logger.info(f"Kafka brokers: {kafka_config.bootstrap_servers}")
        self.logger.info(f"Topics: {kafka_config.sensor_topic}, {kafka_config.alert_topic}")
        
        return AppConfig(
            service=service_config,
            kafka=kafka_config
        )
    
    def get_config(self) -> AppConfig:
        """
        Retourne la configuration complète.
        
        Returns:
            Configuration de l'application
        """
        return self.config
    
    def get_kafka_topics_config(self) -> List[Dict[str, Any]]:
        """
        Retourne la configuration des topics Kafka à créer.
        
        Returns:
            Liste des configurations de topics
        """
        return [
            {
                "name": self.config.kafka.sensor_topic,
                "partitions": int(os.getenv('KAFKA_SENSOR_TOPIC_PARTITIONS', '1')),
                "replication": int(os.getenv('KAFKA_SENSOR_TOPIC_REPLICATION', '1'))
            },
            {
                "name": self.config.kafka.alert_topic,
                "partitions": int(os.getenv('KAFKA_ALERT_TOPIC_PARTITIONS', '1')),
                "replication": int(os.getenv('KAFKA_ALERT_TOPIC_REPLICATION', '1'))
            }
        ]
    
    def get_service_dict(self) -> Dict[str, Any]:
        """
        Retourne la configuration du service sous forme de dictionnaire.
        
        Utile pour passer aux routeurs et autres composants.
        
        Returns:
            Configuration du service en dictionnaire
        """
        return {
            'name': self.config.service.name,
            'version': self.config.service.version,
            'description': self.config.service.description,
            'sensor_topic': self.config.kafka.sensor_topic,
            'alert_topic': self.config.kafka.alert_topic
        }
    
    def setup_application_logging(self):
        """
        Configure le logging au niveau de l'application.
        
        Applique le niveau de log configuré et le formatage.
        """
        log_level = getattr(logging, self.config.service.log_level, logging.INFO)
        
        # Configuration du format de log
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        if self.config.service.debug:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        
        # Configuration du logging root
        logging.basicConfig(
            level=log_level,
            format=log_format,
            force=True  # Force la reconfiguration
        )
        
        # Réduire le niveau de log pour certains modules tiers
        logging.getLogger('kafka').setLevel(logging.WARNING)
        logging.getLogger('faker').setLevel(logging.WARNING)
        
        self.logger.info(f"Logging configured - Level: {self.config.service.log_level}")
    
    def validate_config(self) -> bool:
        """
        Valide la configuration chargée.
        
        Returns:
            True si la configuration est valide, False sinon
        """
        try:
            # Validation des brokers Kafka
            if not self.config.kafka.bootstrap_servers:
                self.logger.error("No Kafka bootstrap servers configured")
                return False
            
            # Validation du port
            if not (1 <= self.config.service.port <= 65535):
                self.logger.error(f"Invalid port: {self.config.service.port}")
                return False
            
            # Validation des topics
            if not self.config.kafka.sensor_topic or not self.config.kafka.alert_topic:
                self.logger.error("Kafka topics not properly configured")
                return False
            
            self.logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            return False
    
    def print_config_summary(self):
        """Affiche un résumé de la configuration pour debugging."""
        config = self.config
        
        print("\n" + "=" * 60)
        print("📋 Configuration Summary")
        print("=" * 60)
        print(f"Service: {config.service.name} v{config.service.version}")
        print(f"Host: {config.service.host}:{config.service.port}")
        print(f"Log Level: {config.service.log_level}")
        print(f"Debug Mode: {config.service.debug}")
        print(f"Kafka Brokers: {', '.join(config.kafka.bootstrap_servers)}")
        print(f"Sensor Topic: {config.kafka.sensor_topic}")
        print(f"Alert Topic: {config.kafka.alert_topic}")
        print(f"Client ID: {config.kafka.client_id}")
        print("=" * 60 + "\n")


# Instance globale du gestionnaire de configuration
config_manager = ConfigManager()