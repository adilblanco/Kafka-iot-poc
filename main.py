"""
Point d'entrée principal de l'application IoT Sensor Producer

Ce module orchestre l'initialisation de tous les composants
et configure l'application FastAPI avec ses routeurs.
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# Imports des modules de l'application
from core.config import config_manager
from services.kafka_service import KafkaManager
from services.sensor_simulator import SensorSimulator
from api.health import create_health_router
from api.sensors import create_sensors_router
from api.stats import create_stats_router, create_info_router


# Configuration du logging
logger = logging.getLogger(__name__)

# Instances globales
kafka_manager: KafkaManager = None
sensor_simulator: SensorSimulator = None
statistics = {
    'total_events_published': 0,
    'total_sensors_triggered': 0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire du cycle de vie de l'application.
    
    Gère l'initialisation et la fermeture propre des ressources.
    """
    # Startup
    logger.info("=" * 80)
    logger.info("IoT Sensor Producer (Modular Version) Starting...")
    logger.info("=" * 80)
    
    # Chargement et validation de la configuration
    config = config_manager.get_config()
    if not config_manager.validate_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Affichage du résumé de configuration
    if config.service.debug:
        config_manager.print_config_summary()
    
    # Initialisation du gestionnaire Kafka
    global kafka_manager
    kafka_manager = KafkaManager(
        bootstrap_servers=config.kafka.bootstrap_servers,
        client_id=config.kafka.client_id
    )
    
    if not kafka_manager.initialize():
        logger.error("Failed to initialize Kafka. Exiting.")
        sys.exit(1)
    
    # Création des topics Kafka
    topics_config = config_manager.get_kafka_topics_config()
    if not kafka_manager.ensure_topics_exist(topics_config):
        logger.warning("Could not ensure all topics exist")
    
    # Initialisation du simulateur de capteurs
    global sensor_simulator
    sensor_simulator = SensorSimulator()
    
    # Configuration des routeurs maintenant que tous les services sont initialisés
    setup_routers(app)
    
    logger.info("All services initialized successfully")
    logger.info(f"API available at: http://{config.service.host}:{config.service.port}")
    logger.info(f"Documentation: http://{config.service.host}:{config.service.port}/docs")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("\nShutting down IoT Sensor Producer...")
    
    if kafka_manager:
        kafka_manager.close()
    
    logger.info("Goodbye!")


def create_application() -> FastAPI:
    """
    Crée et configure l'application FastAPI.
    
    Returns:
        Instance configurée de FastAPI
    """
    # Configuration du logging avant toute chose
    config_manager.setup_application_logging()
    
    config = config_manager.get_config()
    
    # Création de l'application FastAPI
    app = FastAPI(
        title=config.service.name,
        description=config.service.description,
        version=config.service.version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configuration CORS pour les démos web
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En production, spécifier les domaines autorisés
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Configuration des gestionnaires d'erreurs globaux
    setup_error_handlers(app)
    
    # Ajout des routeurs (sera fait dans setup_routers après l'initialisation)
    return app


def setup_routers(app: FastAPI):
    """
    Configure et ajoute tous les routeurs à l'application.
    
    Cette fonction est appelée après l'initialisation des services
    car les routeurs ont besoin des instances globales.
    """
    config = config_manager.get_config()
    service_config = config_manager.get_service_dict()
    
    try:
        # Routeur de santé
        health_router = create_health_router(kafka_manager)
        app.include_router(health_router)
        
        # Routeur des capteurs
        sensors_router = create_sensors_router(kafka_manager, sensor_simulator, statistics)
        app.include_router(sensors_router)
        
        # Routeur des statistiques
        stats_router = create_stats_router(kafka_manager, sensor_simulator, statistics, service_config)
        app.include_router(stats_router)
        
        # Routeur d'information générale
        info_router = create_info_router(service_config)
        app.include_router(info_router)
        
        logger.info("All API routers configured successfully")
        
    except Exception as e:
        logger.error(f"Failed to setup routers: {str(e)}")
        raise


def setup_error_handlers(app: FastAPI):
    """
    Configure les gestionnaires d'erreurs globaux.
    
    Args:
        app: Instance FastAPI
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Gestionnaire pour les HTTPExceptions."""
        logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error_type": "http_exception",
                "detail": exc.detail,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Gestionnaire pour les exceptions générales non gérées."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_type": "internal_server_error",
                "detail": "An internal server error occurred",
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }
        )


# Création de l'application
app = create_application()


if __name__ == "__main__":
    """
    Point d'entrée pour l'exécution directe.
    
    En production, utiliser un serveur WSGI comme uvicorn:
    uvicorn main:app --host 0.0.0.0 --port 5000
    """
    import uvicorn
    
    config = config_manager.get_config()
    
    # Configuration d'uvicorn
    uvicorn_config = {
        "app": "main:app",
        "host": config.service.host,
        "port": config.service.port,
        "log_level": config.service.log_level.lower(),
        "access_log": True,
        "reload": config.service.debug  # Auto-reload en mode debug
    }
    
    logger.info(f"Starting server with uvicorn: {config.service.host}:{config.service.port}")
    
    uvicorn.run(**uvicorn_config)
