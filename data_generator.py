import pandas as pd
import numpy as np
from typing import Dict, Any

def generate_historical_data(num_trucks: int = 1000, sim_time_hours: int = 24) -> pd.DataFrame:
    """
    Genera un conjunto de datos simulado/histórico para analizar el comportamiento
    base del flujo de camiones en el terminal.
    
    Args:
        num_trucks: Número de camiones a simular.
        sim_time_hours: Horas de simulación para distribuir las llegadas.
        
    Returns:
        pd.DataFrame con los datos históricos simulados.
    """
    np.random.seed(42)  # Para reproducibilidad en la interfaz
    
    # Distribuir las llegadas a lo largo del tiempo de simulación
    avg_inter_arrival = (sim_time_hours * 60.0) / num_trucks
    arrival_times = np.random.exponential(scale=avg_inter_arrival, size=num_trucks)
    cumulative_arrival = np.cumsum(arrival_times)
    
    # Tiempo de validación en puerta (gate-in/gate-out) en minutos
    # Base de 3 minutos + varianza
    validation_times = np.random.normal(loc=3.0, scale=1.0, size=num_trucks)
    validation_times = np.clip(validation_times, 1.0, 10.0)
    
    # Tasa de falla en validaciones (documentos erróneos)
    # Asumimos que un 15% de los camiones tienen problemas documentales que aumentan su tiempo
    has_error = np.random.choice([False, True], size=num_trucks, p=[0.85, 0.15])
    
    # Si hay error, el tiempo de validación aumenta considerablemente
    extra_time_for_errors = np.where(has_error, np.random.uniform(5.0, 20.0, size=num_trucks), 0)
    total_validation_times = validation_times + extra_time_for_errors
    
    data = {
        'truck_id': [f"TRK-{i:04d}" for i in range(1, num_trucks + 1)],
        'arrival_minute': cumulative_arrival,
        'base_validation_time': validation_times,
        'has_document_error': has_error,
        'total_validation_time': total_validation_times
    }
    
    df = pd.DataFrame(data)
    return df

def get_simulation_parameters() -> Dict[str, Any]:
    """
    Devuelve los parámetros por defecto para la simulación.
    """
    return {
        'arrival_rate_per_hour': 20, # Camiones por hora promedio en escenario base
        'gate_capacity': 2,          # Número de puertas operativas
        'yard_capacity': 100,        # Capacidad máxima del patio en camiones
        'base_error_rate': 0.15,     # 15% de camiones con error documental
        'sim_time_hours': 24         # Tiempo de simulación (1 día)
    }

if __name__ == "__main__":
    # Test simple
    df = generate_historical_data(10)
    print("Muestra de datos generados:")
    print(df.head())
    print("\nParámetros por defecto:")
    print(get_simulation_parameters())
