import simpy
import pandas as pd
from typing import Dict, Any, Tuple

class PortTerminalSimulation:
    def __init__(self, env: simpy.Environment, df: pd.DataFrame, params: Dict[str, Any], is_dynamic: bool):
        self.env = env
        self.df = df
        self.params = params
        self.is_dynamic = is_dynamic
        
        # Recursos
        self.gate = simpy.Resource(env, capacity=params['gate_capacity'])
        self.yard = simpy.Resource(env, capacity=params['yard_capacity'])
        
        self.results = []
        
        # Para el VBS dinámico, controlamos la tasa de fallas reciente (ventana móvil simple)
        self.recent_errors = 0
        self.total_recent = 0

    def get_yard_occupancy(self):
        return self.yard.count / self.yard.capacity

    def truck_process(self, truck_id: str, total_val_time: float, has_error: bool, scheduled_arrival: float):
        
        # El camión espera en su origen hasta la hora de su cita original
        if scheduled_arrival > self.env.now:
            yield self.env.timeout(scheduled_arrival - self.env.now)
            
        actual_arrival = scheduled_arrival
        
        virtual_wait_yard = 0.0
        virtual_wait_gate = 0.0
        
        # Escenario Dinámico: VBS actúa como sistema Pull (Lean)
        if self.is_dynamic:
            # Mientras haya mucha fila en puerta (> 2 veces la capacidad) o el patio esté a > 60%
            # El VBS retiene al camión virtualmente ("Espera en tu almacén")
            while True:
                gate_full = len(self.gate.queue) > (self.gate.capacity * 2)
                yard_full = self.get_yard_occupancy() > 0.85
                
                if not (gate_full or yard_full):
                    break
                
                yield self.env.timeout(10.0) # Revisa cada 10 mins
                actual_arrival += 10.0
                
                if yard_full:
                    virtual_wait_yard += 10.0
                else:
                    virtual_wait_gate += 10.0
                
        # Llegada física al terminal
        arrival_time = self.env.now
        
        # Actualizar métricas (para lógica auxiliar si se necesita)
        self.total_recent += 1
        if has_error:
            self.recent_errors += 1
            
        # Solicitud de puerta (Gate)
        with self.gate.request() as gate_req:
            yield gate_req
            wait_time_gate = self.env.now - arrival_time
            
            # Proceso de validación en puerta
            yield self.env.timeout(total_val_time)
            gate_end_time = self.env.now
            
        # Solicitud de entrada al patio (Yard)
        # Si el patio está lleno, el camión espera bloqueando la salida de la puerta o en una zona pulmón
        with self.yard.request() as yard_req:
            yield yard_req
            wait_time_yard = self.env.now - gate_end_time
            
            # Guardar resultados
            virtual_wait_time = virtual_wait_yard + virtual_wait_gate
            total_wait_time = virtual_wait_time + wait_time_gate + wait_time_yard
            
            self.results.append({
                'truck_id': truck_id,
                'scheduled_arrival': scheduled_arrival,
                'actual_arrival': arrival_time,
                'virtual_wait_time': virtual_wait_time,
                'virtual_wait_yard': virtual_wait_yard,
                'virtual_wait_gate': virtual_wait_gate,
                'wait_time_gate': wait_time_gate,
                'wait_time_yard': wait_time_yard,
                'total_wait_time': total_wait_time,
                'total_val_time': total_val_time,
                'has_error': has_error,
                'yard_occupancy_at_arrival': self.get_yard_occupancy()
            })
            
            # Tiempo operativo dentro del patio con penalización por congestión (Lean)
            # A mayor ocupación, mayor tiempo de maniobra/barajado de contenedores (shuffling delay)
            occupancy = self.get_yard_occupancy()
            yard_stay_time = 45.0
            if occupancy > 0.70:
                yard_stay_time *= (1.0 + 1.5 * (occupancy - 0.70))
            
            yield self.env.timeout(yard_stay_time)
            
        # Reducir el historial reciente para mantener una ventana móvil
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
    """
    Ejecuta ambos escenarios de simulación y devuelve los resultados.
    """
    # Ejecutar escenario Estático
    env_static = simpy.Environment()
    sim_static = PortTerminalSimulation(env_static, df, params, is_dynamic=False)
    sim_static.run()
    env_static.run()  # Corre hasta completar todos los eventos
    df_static = pd.DataFrame(sim_static.results)
    
    # Filtrar para conservar solo los camiones que debían llegar dentro del tiempo de la simulación
    if not df_static.empty:
        df_static = df_static[df_static['scheduled_arrival'] <= params['sim_time_hours'] * 60]
        df_static['scenario'] = 'Estático'
    
    # Ejecutar escenario Dinámico
    env_dynamic = simpy.Environment()
    sim_dynamic = PortTerminalSimulation(env_dynamic, df, params, is_dynamic=True)
    sim_dynamic.run()
    env_dynamic.run()  # Corre hasta completar todos los eventos
    df_dynamic = pd.DataFrame(sim_dynamic.results)
    
    # Filtrar para conservar solo los camiones que debían llegar dentro del tiempo de la simulación
    if not df_dynamic.empty:
        df_dynamic = df_dynamic[df_dynamic['scheduled_arrival'] <= params['sim_time_hours'] * 60]
        df_dynamic['scenario'] = 'Dinámico'
    
    return df_static, df_dynamic
