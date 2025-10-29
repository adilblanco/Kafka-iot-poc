"""
Simulateur de capteurs IoT pour le système de monitoring

Ce module contient la logique de génération de données de capteurs
réalistes pour le système de bâtiment intelligent. Il simule différents
types de capteurs avec des patterns de données cohérents.
"""

import random
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from faker import Faker

from models import SensorData, SensorAlert


logger = logging.getLogger(__name__)


class SensorSimulator:
    """
    Simulateur de capteurs environnementaux pour bâtiment intelligent.
    
    Cette classe génère des données réalistes pour différents types de capteurs
    (température, humidité, pression) avec des variations cohérentes et la
    possibilité de simuler des anomalies.
    """
    
    def __init__(self):
        """Initialise le simulateur avec les paramètres par défaut."""
        self.fake = Faker('fr_FR')  # Locale française pour les noms de lieux
        self.event_counter = 0
        
        # Configuration des plages normales de valeurs
        self.normal_ranges = {
            "temperature": {"mean": 22.0, "std": 2.0, "min": 15.0, "max": 35.0},
            "humidity": {"mean": 55.0, "std": 8.0, "min": 20.0, "max": 95.0},
            "pressure": {"mean": 1013.25, "std": 5.0, "min": 980.0, "max": 1040.0},
            "battery": {"min": 0.3, "max": 1.0}
        }
        
        # Seuils d'alerte pour la détection d'anomalies
        self.alert_thresholds = {
            "temperature": {"low": 18.0, "high": 26.0, "critical": 30.0},
            "humidity": {"low": 30.0, "high": 80.0, "critical": 90.0},
            "pressure": {"low": 1000.0, "high": 1025.0},
            "battery": {"low": 0.2, "critical": 0.1}
        }
        
        # Seuils d'alerte pour la détection d'anomalies
        self.alert_thresholds = {
            "temperature": {"low": 18.0, "high": 26.0, "critical": 30.0},
            "humidity": {"low": 30.0, "high": 80.0, "critical": 90.0},
            "pressure": {"low": 1000.0, "high": 1025.0},
            "battery": {"low": 0.2, "critical": 0.1}
        }
    
    def generate_sensor_data(self, sensor_id: str) -> SensorData:
        """
        Génère des données réalistes pour un capteur donné.
        
        Args:
            sensor_id: Identifiant unique du capteur
        
        Returns:
            Instance de SensorData avec données générées
        """
        # Génération de température avec distribution gaussienne
        temp_config = self.normal_ranges["temperature"]
        temperature = random.gauss(temp_config["mean"], temp_config["std"])
        temperature = max(temp_config["min"], min(temp_config["max"], temperature))
        temperature = round(temperature, 2)
        
        # Génération d'humidité (corrélée à la température)
        humid_config = self.normal_ranges["humidity"]
        # L'humidité tend à être inversement corrélée à la température
        humidity_adjustment = (temperature - temp_config["mean"]) * -2
        humidity = random.gauss(humid_config["mean"] + humidity_adjustment, humid_config["std"])
        humidity = max(humid_config["min"], min(humid_config["max"], humidity))
        humidity = round(humidity, 2)
        
        # Génération de pression atmosphérique
        pressure_config = self.normal_ranges["pressure"]
        pressure = random.gauss(pressure_config["mean"], pressure_config["std"])
        pressure = max(pressure_config["min"], min(pressure_config["max"], pressure))
        pressure = round(pressure, 2)
        
        # Niveau de batterie (dégradation lente)
        battery_config = self.normal_ranges["battery"]
        battery_level = random.uniform(battery_config["min"], battery_config["max"])
        battery_level = round(battery_level, 2)
        
        self.event_counter += 1
        
        return SensorData(
            sensor_id=sensor_id,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            battery_level=battery_level
        )
    
    def generate_custom_sensor_data(
        self, 
        sensor_id: str, 
        temperature: float,
        humidity: float,
        pressure: Optional[float] = None,
        battery_level: Optional[float] = None
    ) -> SensorData:
        """
        Génère des données de capteur avec paramètres personnalisés.
        
        Args:
            sensor_id: Identifiant du capteur
            temperature: Température spécifiée
            humidity: Humidité spécifiée
            pressure: Pression (optionnel, généré si non fourni)
            battery_level: Niveau batterie (optionnel, généré si non fourni)
        
        Returns:
            Instance de SensorData avec paramètres personnalisés
        """
        if pressure is None:
            pressure_config = self.normal_ranges["pressure"]
            pressure = round(random.gauss(pressure_config["mean"], pressure_config["std"]), 2)
        
        if battery_level is None:
            battery_config = self.normal_ranges["battery"]
            battery_level = round(random.uniform(battery_config["min"], battery_config["max"]), 2)
        
        return SensorData(
            sensor_id=sensor_id,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            temperature=temperature,
            humidity=humidity,
            pressure=pressure,
            battery_level=battery_level
        )
    
    def generate_batch(self, count: int) -> List[SensorData]:
        """
        Génère un lot de données de capteurs.
        
        Args:
            count: Nombre de capteurs à simuler
        
        Returns:
            Liste de données de capteurs générées
        """
        batch = []
        
        for i in range(1, count + 1):
            sensor_id = f'sensor_{i:03d}'
            data = self.generate_sensor_data(sensor_id)
            batch.append(data)
        
        logger.info(f"Generated batch of {count} sensor readings")
        return batch
    
    def detect_anomalies(self, sensor_data: SensorData) -> List[SensorAlert]:
        """
        Détecte les anomalies dans les données d'un capteur.
        
        Args:
            sensor_data: Données du capteur à analyser
        
        Returns:
            Liste d'alertes détectées
        """
        alerts = []
        
        # Vérification température
        temp_alerts = self._check_temperature_alerts(sensor_data)
        alerts.extend(temp_alerts)
        
        # Vérification humidité
        humidity_alerts = self._check_humidity_alerts(sensor_data)
        alerts.extend(humidity_alerts)
        
        # Vérification pression
        pressure_alerts = self._check_pressure_alerts(sensor_data)
        alerts.extend(pressure_alerts)
        
        # Vérification batterie
        battery_alerts = self._check_battery_alerts(sensor_data)
        alerts.extend(battery_alerts)
        
        return alerts
    
    def _check_temperature_alerts(self, sensor_data: SensorData) -> List[SensorAlert]:
        """Vérifie les alertes de température."""
        alerts = []
        temp = sensor_data.temperature
        thresholds = self.alert_thresholds["temperature"]
        
        if temp >= thresholds["critical"]:
            alerts.append(self._create_alert(
                sensor_data, "temperature", "critical", temp, thresholds["critical"],
                f"Température critique: {temp}°C (seuil: {thresholds['critical']}°C)"
            ))
        elif temp >= thresholds["high"]:
            alerts.append(self._create_alert(
                sensor_data, "temperature", "high", temp, thresholds["high"],
                f"Température élevée: {temp}°C (seuil: {thresholds['high']}°C)"
            ))
        elif temp <= thresholds["low"]:
            alerts.append(self._create_alert(
                sensor_data, "temperature", "low", temp, thresholds["low"],
                f"Température basse: {temp}°C (seuil: {thresholds['low']}°C)"
            ))
        
        return alerts
    
    def _check_humidity_alerts(self, sensor_data: SensorData) -> List[SensorAlert]:
        """Vérifie les alertes d'humidité."""
        alerts = []
        humidity = sensor_data.humidity
        thresholds = self.alert_thresholds["humidity"]
        
        if humidity >= thresholds["critical"]:
            alerts.append(self._create_alert(
                sensor_data, "humidity", "critical", humidity, thresholds["critical"],
                f"Humidité critique: {humidity}% (seuil: {thresholds['critical']}%)"
            ))
        elif humidity >= thresholds["high"]:
            alerts.append(self._create_alert(
                sensor_data, "humidity", "high", humidity, thresholds["high"],
                f"Humidité élevée: {humidity}% (seuil: {thresholds['high']}%)"
            ))
        elif humidity <= thresholds["low"]:
            alerts.append(self._create_alert(
                sensor_data, "humidity", "low", humidity, thresholds["low"],
                f"Humidité basse: {humidity}% (seuil: {thresholds['low']}%)"
            ))
        
        return alerts
    
    def _check_pressure_alerts(self, sensor_data: SensorData) -> List[SensorAlert]:
        """Vérifie les alertes de pression."""
        alerts = []
        pressure = sensor_data.pressure
        thresholds = self.alert_thresholds["pressure"]
        
        if pressure >= thresholds["high"]:
            alerts.append(self._create_alert(
                sensor_data, "pressure", "medium", pressure, thresholds["high"],
                f"Pression élevée: {pressure} hPa (seuil: {thresholds['high']} hPa)"
            ))
        elif pressure <= thresholds["low"]:
            alerts.append(self._create_alert(
                sensor_data, "pressure", "medium", pressure, thresholds["low"],
                f"Pression basse: {pressure} hPa (seuil: {thresholds['low']} hPa)"
            ))
        
        return alerts
    
    def _check_battery_alerts(self, sensor_data: SensorData) -> List[SensorAlert]:
        """Vérifie les alertes de batterie."""
        alerts = []
        battery = sensor_data.battery_level
        thresholds = self.alert_thresholds["battery"]
        
        if battery <= thresholds["critical"]:
            alerts.append(self._create_alert(
                sensor_data, "battery", "critical", battery, thresholds["critical"],
                f"Batterie critique: {battery*100:.0f}% (seuil: {thresholds['critical']*100:.0f}%)"
            ))
        elif battery <= thresholds["low"]:
            alerts.append(self._create_alert(
                sensor_data, "battery", "medium", battery, thresholds["low"],
                f"Batterie faible: {battery*100:.0f}% (seuil: {thresholds['low']*100:.0f}%)"
            ))
        
        return alerts
    
    def _create_alert(
        self,
        sensor_data: SensorData,
        alert_type: str,
        severity: str,
        value: float,
        threshold: float,
        message: str
    ) -> SensorAlert:
        """Crée une alerte standardisée."""
        alert_id = f"alert_{self.event_counter}_{alert_type}_{int(datetime.utcnow().timestamp())}"
        
        return SensorAlert(
            alert_id=alert_id,
            sensor_id=sensor_data.sensor_id,
            alert_type=alert_type,
            severity=severity,
            value=value,
            threshold=threshold,
            message=message,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du simulateur.
        
        Returns:
            Dictionnaire avec les statistiques de simulation
        """
        return {
            "total_events_generated": self.event_counter,
            "normal_ranges": self.normal_ranges,
            "alert_thresholds": self.alert_thresholds,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }