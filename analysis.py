import pandas as pd
from typing import Dict

def analyze_root_causes(df: pd.DataFrame) -> Dict[str, float]:
    """
    Analiza los datos de la simulación para aislar matemáticamente 
    las causas raíz del tiempo de espera en minutos absolutos.
    """
    if df.empty:
        return {
            'Falta de espacio en patio': 0,
            'Errores en documentos': 0,
            'Llegada de muchos camiones a la vez': 0
        }
        
    # 1. Falta de espacio en patio (espera física + virtual por patio lleno)
    virtual_wait_yard_sum = df['virtual_wait_yard'].sum() if 'virtual_wait_yard' in df.columns else 0.0
    total_wait_yard = df['wait_time_yard'].sum() + virtual_wait_yard_sum
    
    # 2. Errores en documentos
    base_avg = df[~df['has_error']]['total_val_time'].mean()
    if pd.isna(base_avg): 
        base_avg = 3.0
    
    error_extra_time = df[df['has_error']]['total_val_time'] - base_avg
    total_error_impact = error_extra_time[error_extra_time > 0].sum()
    
    # 3. Llegadas masivas (espera física en puerta + virtual por cola en puerta)
    virtual_wait_gate_sum = df['virtual_wait_gate'].sum() if 'virtual_wait_gate' in df.columns else 0.0
    total_wait_gate = df['wait_time_gate'].sum() + virtual_wait_gate_sum
    arrival_peaks_impact = max(0, total_wait_gate - total_error_impact)
        
    return {
        'Falta de espacio en patio': total_wait_yard,
        'Errores en documentos': total_error_impact,
        'Llegada de muchos camiones a la vez': arrival_peaks_impact
    }

def calculate_kpis(df_static: pd.DataFrame, df_dynamic: pd.DataFrame, sim_hours: int) -> Dict[str, Dict[str, float]]:
    """
    Calcula los KPIs clave (Wait Time promedio y Throughput por hora).
    """
    def get_kpis(df):
        if df.empty:
            return {'avg_wait_time': 0, 'throughput_per_hour': 0}
        
        # Promedio de espera total en minutos (Gate + Yard)
        avg_wait = df['total_wait_time'].mean()
        
        # Throughput = Total camiones procesados / horas de simulación
        throughput = len(df) / sim_hours
        
        return {'avg_wait_time': avg_wait, 'throughput_per_hour': throughput}
        
    return {
        'Static': get_kpis(df_static),
        'Dynamic': get_kpis(df_dynamic)
    }
