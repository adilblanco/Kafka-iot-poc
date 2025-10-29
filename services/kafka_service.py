"""
Service de gestion Kafka pour le système IoT

Ce module encapsule toute la logique de connexion, configuration
et publication vers Kafka, en isolant ces responsabilités du reste
de l'application.
"""

import json
import logging
from typing import List, Optional
from kafka import KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError


logger = logging.getLogger(__name__)


class KafkaManager:
    """
    Gestionnaire centralisé pour toutes les opérations Kafka.
    
    Cette classe encapsule la logique de connexion, création de topics
    et publication de messages vers Kafka. Elle gère également la
    résilience et la gestion d'erreurs.
    """
    
    def __init__(self, bootstrap_servers: List[str], client_id: str = "iot_producer"):
        """
        Initialise le gestionnaire Kafka.
        
        Args:
            bootstrap_servers: Liste des serveurs Kafka
            client_id: Identifiant du client Kafka
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.producer: Optional[KafkaProducer] = None
        self.admin_client: Optional[KafkaAdminClient] = None
        self.is_connected = False
        
    def initialize(self) -> bool:
        """
        Initialise les clients Kafka (admin et producer).
        
        Returns:
            True si la connexion est réussie, False sinon
        """
        try:
            # Création du client administrateur
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f'{self.client_id}_admin'
            )
            
            # Création du producteur
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',  # Attendre la confirmation de tous les replicas
                retries=3,   # Nombre de tentatives en cas d'échec
                linger_ms=10,  # Attendre 10ms pour batching
                compression_type='gzip'  # Compression des messages
            )
            
            self.is_connected = True
            logger.info(f"Connected to Kafka brokers: {self.bootstrap_servers}")
            self._ensure_topics_exist()
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            self.is_connected = False
            return False
    
    def ensure_topics_exist(self, topics_config: List[dict]) -> bool:
        """
        Crée les topics Kafka s'ils n'existent pas.
        
        Args:
            topics_config: Liste de configurations de topics
                Exemple: [{"name": "sensors", "partitions": 1, "replication": 1}]
        
        Returns:
            True si les topics sont créés/existent, False sinon
        """
        if not self.admin_client:
            logger.error("Admin client not initialized")
            return False
        
        try:
            topics = []
            for config in topics_config:
                topic = NewTopic(
                    name=config["name"],
                    num_partitions=config.get("partitions", 1),
                    replication_factor=config.get("replication", 1)
                )
                topics.append(topic)
            
            # Tentative de création des topics
            self.admin_client.create_topics(new_topics=topics, validate_only=False)
            
            topic_names = [config["name"] for config in topics_config]
            logger.info(f"Topics ensured: {topic_names}")
            return True
            
        except Exception as e:
            # Topics peuvent déjà exister
            if "TopicAlreadyExistsException" in str(type(e)):
                logger.info("Topics already exist")
                return True
            else:
                logger.warning(f"Could not ensure topics: {str(e)}")
                return False
    
    def publish_message(self, topic: str, message: dict) -> bool:
        """
        Publie un message sur un topic Kafka.
        
        Args:
            topic: Nom du topic Kafka
            message: Message à publier (dict)
        
        Returns:
            True si la publication réussit, False sinon
        """
        if not self.is_connected or not self.producer:
            logger.error("Kafka producer not connected")
            return False
        
        try:
            # Publication asynchrone avec callback
            future = self.producer.send(topic, value=message)
            
            # Attendre la confirmation (synchrone pour la démonstration)
            record_metadata = future.get(timeout=10)
            
            logger.debug(
                f"Message published to {topic} | "
                f"Partition: {record_metadata.partition}, "
                f"Offset: {record_metadata.offset}"
            )
            return True
        
        except KafkaError as e:
            logger.error(f"Kafka error publishing message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing message: {str(e)}")
            return False
    
    def publish_batch(self, topic: str, messages: List[dict]) -> int:
        """
        Publie un lot de messages sur un topic Kafka.
        
        Args:
            topic: Nom du topic Kafka
            messages: Liste de messages à publier
        
        Returns:
            Nombre de messages publiés avec succès
        """
        if not self.is_connected or not self.producer:
            logger.error("Kafka producer not connected")
            return 0
        
        published_count = 0
        
        for message in messages:
            if self.publish_message(topic, message):
                published_count += 1
        
        # Forcer l'envoi de tous les messages en buffer
        self.producer.flush()
        
        logger.info(f"Batch published: {published_count}/{len(messages)} messages")
        return published_count
    
    def get_connection_status(self) -> dict:
        """
        Retourne l'état de la connexion Kafka.
        
        Returns:
            Dictionnaire avec les informations de connexion
        """
        return {
            "connected": self.is_connected,
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "producer_available": self.producer is not None,
            "admin_client_available": self.admin_client is not None
        }
    
    def close(self) -> None:
        """
        Ferme proprement les connexions Kafka.
        """
        try:
            if self.producer:
                self.producer.flush()  # S'assurer que tous les messages sont envoyés
                self.producer.close()
                logger.info("Kafka producer closed")
            
            if self.admin_client:
                self.admin_client.close()
                logger.info("Kafka admin client closed")
            
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Error closing Kafka connections: {str(e)}")


class KafkaHealthChecker:
    """
    Utilitaire pour vérifier la santé de la connexion Kafka.
    """
    
    @staticmethod
    def check_connectivity(bootstrap_servers: List[str], timeout: int = 5) -> bool:
        """
        Vérifie la connectivité vers les brokers Kafka.
        
        Args:
            bootstrap_servers: Liste des serveurs Kafka
            timeout: Timeout en secondes
        
        Returns:
            True si au moins un broker est accessible
        """
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                request_timeout_ms=timeout * 1000
            )
            
            # Tentative de récupération des métadonnées
            metadata = admin_client.describe_topics([])  # Topics vides pour test
            admin_client.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Kafka connectivity check failed: {str(e)}")
            return False