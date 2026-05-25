# Informe Final: PoC del Sistema Dinámico de Agendamiento de Vehículos (VBS)

## 1. Introducción y Objetivo
El objetivo de este proyecto fue programar una Prueba de Concepto (PoC) para un terminal portuario que demostrara el valor de un **Sistema Dinámico de Agendamiento de Vehículos (VBS)**.

Utilizando la metodología **Lean/Gemba**, se diseñó un simulador para aislar y diagnosticar cuellos de botella, evidenciando de forma matemática cómo un modelo dinámico de control de inventario (*Pull*) reduce drásticamente la congestión física frente a un modelo tradicional (*Push* o Estático).

## 2. Evolución y Metodología (Paso a Paso)

El desarrollo se construyó de manera iterativa:

### Fase 1: Arquitectura Base
Se definió un stack basado en **Python**, **SimPy** (eventos discretos), **Pandas** y **Streamlit** para la interfaz. El código se dividió en 4 módulos independientes (`data_generator.py`, `simulation.py`, `analysis.py` y `app.py`) para mantener la limpieza y la mantenibilidad.

### Fase 2: Humanización de la Interfaz
Tras la primera iteración técnica, se optimizó el Dashboard de Streamlit para "humanizarlo":
- **Claridad Visual:** Se eliminaron emojis y se optó por una paleta de colores corporativa (Gris para el modelo tradicional y Azul para el inteligente).
- **Interactividad en Tiempo Real:** Se eliminó el botón de recarga, conectando los controles directamente al motor matemático para un cálculo en tiempo real.
- **Educación al Usuario:** Se agregaron "Tooltips" (íconos de interrogación) explicando cada métrica con analogías simples (como la de un restaurante con o sin reserva) y se sustituyeron los gráficos complejos por comparativas directas y fáciles de entender.

### Fase 3: Resolución del Sistema Pull (El Bug de Congestión)
Al inicio, el VBS no reflejaba diferencia entre escenarios. El sistema evaluaba la congestión al segundo "cero" de simulación, permitiendo el ingreso incontrolado. 
**La solución clave:** Se reprogramó el motor en `simulation.py` para evaluar el nivel de fila en las puertas y la ocupación del patio en el *milisegundo exacto* en que el camión pretendía salir de su almacén. Al retenerlos virtualmente en el origen (sistema Pull), las gráficas demostraron por fin la verdadera eliminación del cuello de botella físico.

---

## 3. Código Fuente del Proyecto

A continuación se documentan los 4 módulos vitales y las dependencias que componen la PoC funcional:

### A. Dependencias (`requirements.txt`)
```text
streamlit
simpy
pandas
plotly
numpy
```

### B. Módulo de Datos (`data_generator.py`)
Encargado de la generación histórica y la simulación estadística de errores documentales y tiempos de atención.

```python
import pandas as pd
import numpy as np
from typing import Dict, Any

def generate_historical_data(num_trucks: int = 1000, sim_time_hours: int = 24) -> pd.DataFrame:
    np.random.seed(42)  # Para reproducibilidad en la interfaz
    
    # Distribuir las llegadas a lo largo del tiempo de simulación
    avg_inter_arrival = (sim_time_hours * 60.0) / num_trucks
    arrival_times = np.random.exponential(scale=avg_inter_arrival, size=num_trucks)
    cumulative_arrival = np.cumsum(arrival_times)
    
    # Tiempo de validación en puerta (gate-in/gate-out) en minutos
    validation_times = np.random.normal(loc=3.0, scale=1.0, size=num_trucks)
    validation_times = np.clip(validation_times, 1.0, 10.0)
    
    # Tasa de falla en validaciones (documentos erróneos)
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
    
    return pd.DataFrame(data)

def get_simulation_parameters() -> Dict[str, Any]:
    return {
        'arrival_rate_per_hour': 20,
        'gate_capacity': 2,
        'yard_capacity': 100,
        'base_error_rate': 0.15,
        'sim_time_hours': 24
    }
```

### C. Motor SimPy (`simulation.py`)
Módulo donde ocurre la "magia" de la simulación de eventos discretos y las reglas del VBS Dinámico (Pull).

```python
import simpy
import pandas as pd
from typing import Dict, Any, Tuple

class PortTerminalSimulation:
    def __init__(self, env: simpy.Environment, df: pd.DataFrame, params: Dict[str, Any], is_dynamic: bool):
        self.env = env
        self.df = df
        self.params = params
        self.is_dynamic = is_dynamic
        self.gate = simpy.Resource(env, capacity=params['gate_capacity'])
        self.yard = simpy.Resource(env, capacity=params['yard_capacity'])
        self.results = []
        self.recent_errors = 0
        self.total_recent = 0

    def get_yard_occupancy(self):
        return self.yard.count / self.yard.capacity

    def truck_process(self, truck_id: str, total_val_time: float, has_error: bool, scheduled_arrival: float):
        # El camión espera en su origen hasta la hora de su cita original
        if scheduled_arrival > self.env.now:
            yield self.env.timeout(scheduled_arrival - self.env.now)
            
        actual_arrival = scheduled_arrival
        
        # Escenario Dinámico: VBS actúa como sistema Pull (Lean)
        if self.is_dynamic:
            # Mientras haya mucha fila en puerta (> 2 veces la capacidad) o el patio esté a > 60%
            # El VBS retiene al camión virtualmente ("Espera en tu almacén")
            while len(self.gate.queue) > (self.gate.capacity * 2) or self.get_yard_occupancy() > 0.60:
                yield self.env.timeout(10.0)
                actual_arrival += 10.0
                
        # Llegada física al terminal
        arrival_time = self.env.now
        
        self.total_recent += 1
        if has_error:
            self.recent_errors += 1
            
        # Proceso de Puerta (Gate)
        with self.gate.request() as gate_req:
            yield gate_req
            wait_time_gate = self.env.now - arrival_time
            yield self.env.timeout(total_val_time)
            gate_end_time = self.env.now
            
        # Proceso de Patio (Yard)
        with self.yard.request() as yard_req:
            yield yard_req
            wait_time_yard = self.env.now - gate_end_time
            total_wait_time = wait_time_gate + wait_time_yard
            
            self.results.append({
                'truck_id': truck_id,
                'scheduled_arrival': scheduled_arrival,
                'actual_arrival': arrival_time,
                'wait_time_gate': wait_time_gate,
                'wait_time_yard': wait_time_yard,
                'total_wait_time': total_wait_time,
                'total_val_time': total_val_time,
                'has_error': has_error,
                'yard_occupancy_at_arrival': self.get_yard_occupancy()
            })
            yield self.env.timeout(45.0) # Tiempo de operación en patio
            
        # Limpiar historial de errores para ventana móvil
        if self.total_recent > 50:
            self.total_recent -= 1
            if has_error and self.recent_errors > 0:
                self.recent_errors -= 1

    def run(self):
        for _, row in self.df.iterrows():
            self.env.process(self.truck_process(
                row['truck_id'],
                row['total_validation_time'],
                row['has_document_error'],
                row['arrival_minute']
            ))

def run_scenarios(df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    env_static = simpy.Environment()
    sim_static = PortTerminalSimulation(env_static, df, params, is_dynamic=False)
    sim_static.run()
    env_static.run(until=params['sim_time_hours'] * 60)
    df_static = pd.DataFrame(sim_static.results)
    if not df_static.empty: df_static['scenario'] = 'Estático'
    
    env_dynamic = simpy.Environment()
    sim_dynamic = PortTerminalSimulation(env_dynamic, df, params, is_dynamic=True)
    sim_dynamic.run()
    env_dynamic.run(until=params['sim_time_hours'] * 60)
    df_dynamic = pd.DataFrame(sim_dynamic.results)
    if not df_dynamic.empty: df_dynamic['scenario'] = 'Dinámico'
    
    return df_static, df_dynamic
```

### D. Análisis Causa Raíz (`analysis.py`)
Encargado de decodificar matemáticamente el "por qué" de las demoras, calculando minutos exactos.

```python
import pandas as pd
from typing import Dict

def analyze_root_causes(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {'Falta de espacio en patio': 0, 'Errores en documentos': 0, 'Llegada masiva': 0}
        
    total_wait_yard = df['wait_time_yard'].sum()
    
    base_avg = df[~df['has_error']]['total_val_time'].mean()
    if pd.isna(base_avg): base_avg = 3.0
    
    error_extra_time = df[df['has_error']]['total_val_time'] - base_avg
    total_error_impact = error_extra_time[error_extra_time > 0].sum()
    
    total_wait_gate = df['wait_time_gate'].sum()
    arrival_peaks_impact = max(0, total_wait_gate - total_error_impact)
        
    return {
        'Falta de espacio en patio': total_wait_yard,
        'Errores en documentos': total_error_impact,
        'Llegada de muchos camiones a la vez': arrival_peaks_impact
    }

def calculate_kpis(df_static: pd.DataFrame, df_dynamic: pd.DataFrame, sim_hours: int) -> Dict[str, Dict[str, float]]:
    def get_kpis(df):
        if df.empty: return {'avg_wait_time': 0, 'throughput_per_hour': 0}
        return {
            'avg_wait_time': df['total_wait_time'].mean(),
            'throughput_per_hour': len(df) / sim_hours
        }
    return {'Static': get_kpis(df_static), 'Dynamic': get_kpis(df_dynamic)}
```

### E. Dashboard Streamlit (`app.py`)
Módulo encargado de la interfaz gráfica y presentación visual de datos para la toma de decisiones. *(El código de este módulo fue implementado y actualizado iterativamente en el proyecto local para la construcción visual).*
