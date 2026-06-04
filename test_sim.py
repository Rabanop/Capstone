import pandas as pd
from data_generator import generate_historical_data
from simulation import run_scenarios

# User parameters
num_trucks = 1800
yard_capacity = 100
gate_capacity = 5
sim_time_hours = 12
error_rate = 0.16

df_base = generate_historical_data(num_trucks=num_trucks, sim_time_hours=sim_time_hours, error_rate=error_rate)

params = {
    'arrival_rate_per_hour': 20,
    'gate_capacity': gate_capacity,
    'yard_capacity': yard_capacity,
    'base_error_rate': error_rate,
    'sim_time_hours': sim_time_hours
}

df_static, df_dynamic = run_scenarios(df_base, params)

df_static['Hora'] = (df_static['scheduled_arrival'] // 60).astype(int)
df_static_agg = df_static.groupby('Hora')['total_wait_time'].mean().reset_index()
print("STATIC WAIT TIME BY HOUR:")
print(df_static_agg)

df_dynamic['Hora'] = (df_dynamic['scheduled_arrival'] // 60).astype(int)
df_dynamic_agg = df_dynamic.groupby('Hora')['total_wait_time'].mean().reset_index()
print("\nDYNAMIC WAIT TIME BY HOUR:")
print(df_dynamic_agg)

print("\nTHROUGHPUT:")
print(f"Static: {len(df_static) / sim_time_hours}")
print(f"Dynamic: {len(df_dynamic) / sim_time_hours}")

print("\nTOTAL WAIT MINUTES:")
print(f"Static: {df_static['total_wait_time'].sum()}")
print(f"Dynamic: {df_dynamic['total_wait_time'].sum()}")
