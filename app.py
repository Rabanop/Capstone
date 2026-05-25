import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_generator import generate_historical_data, get_simulation_parameters
from simulation import run_scenarios
from analysis import analyze_root_causes, calculate_kpis

# Configuración de página
st.set_page_config(page_title="Sistema VBS", layout="wide")

st.title("Sistema de Agendamiento de Vehículos (VBS) - Análisis de Congestión")
st.markdown("""
Esta herramienta demuestra de forma práctica cómo un modelo dinámico de agendamiento 
reduce la congestión frente a un modelo estático tradicional. Se utilizan principios de 
mejora continua para identificar exactamente qué está causando las demoras.
""")

st.info("""
**¿Cuál es la diferencia entre ambos modelos en este análisis?**
* 🔴 **Modelo Estático (Tradicional):** Los camiones llegan al terminal a la hora que quieren o tenían pactada desde un principio. Si el patio adentro está lleno, los camiones simplemente hacen una fila kilométrica afuera, tapando la entrada y la ciudad. Es como ir a un restaurante lleno sin reserva y hacer fila en la calle.
* 🔵 **Modelo Dinámico (Inteligente):** El sistema vigila el patio en tiempo real. Si nota que se está llenando (saturación > 85%), le avisa automáticamente a los camiones que aún no han llegado: *"Ven 30 minutos más tarde"*. El camión "espera" en su origen de forma planificada en lugar de aglomerarse en la puerta física del puerto.
""")

# --- SIDEBAR: Parámetros ---
st.sidebar.header("Parámetros de Simulación")
st.sidebar.markdown("Los gráficos se actualizarán automáticamente al mover estos controles.")

num_trucks = st.sidebar.slider(
    "Cantidad de camiones", 
    min_value=100, max_value=2000, value=500, step=100,
    help="El volumen total de vehículos que llegarán al terminal durante la simulación."
)
yard_capacity = st.sidebar.slider(
    "Capacidad del patio", 
    min_value=50, max_value=500, value=150, step=10,
    help="El número máximo de camiones que el patio puede atender simultáneamente antes de saturarse."
)
gate_capacity = st.sidebar.slider(
    "Puertas operativas", 
    min_value=1, max_value=10, value=3, step=1,
    help="La cantidad de accesos habilitados para validar documentos y permitir la entrada al terminal."
)
sim_time_hours = st.sidebar.slider(
    "Duración (horas)", 
    min_value=8, max_value=48, value=24, step=4,
    help="El tiempo total que durará la simulación virtual."
)

# 1. Generar Datos
df_base = generate_historical_data(num_trucks=num_trucks, sim_time_hours=sim_time_hours)

# Parámetros consolidados
params = get_simulation_parameters()
params.update({
    'yard_capacity': yard_capacity,
    'gate_capacity': gate_capacity,
    'sim_time_hours': sim_time_hours
})

# 2. Correr Simulación
df_static, df_dynamic = run_scenarios(df_base, params)

# 3. Análisis
kpis = calculate_kpis(df_static, df_dynamic, sim_time_hours)
rc_static = analyze_root_causes(df_static)
rc_dynamic = analyze_root_causes(df_dynamic)

# --- DASHBOARD UI ---

st.subheader("Resultados Operativos", help="Muestra la comparación de métricas clave entre el sistema actual (Estático) y el propuesto (Dinámico).")
col1, col2, col3, col4 = st.columns(4)

wait_static = kpis['Static']['avg_wait_time']
wait_dynamic = kpis['Dynamic']['avg_wait_time']
wait_reduction = wait_static - wait_dynamic

col1.metric(
    "Espera Promedio (Estático)", 
    f"{wait_static:.1f} min",
    help="El tiempo medio que espera un camión desde que llega hasta que entra al patio en el modelo tradicional."
)
col2.metric(
    "Espera Promedio (Dinámico)", 
    f"{wait_dynamic:.1f} min", 
    delta=f"-{wait_reduction:.1f} min", delta_color="inverse",
    help="El tiempo medio de espera usando el sistema inteligente que gestiona los flujos."
)

col3.metric(
    "Procesados por Hora (Estático)", 
    f"{kpis['Static']['throughput_per_hour']:.1f}",
    help="La cantidad de camiones que logran entrar al terminal por cada hora de operación bajo el modelo tradicional."
)
col4.metric(
    "Procesados por Hora (Dinámico)", 
    f"{kpis['Dynamic']['throughput_per_hour']:.1f}",
    help="La cantidad de camiones procesados por hora optimizando el ingreso."
)

st.divider()

# Fila 2: Gráficos
col_chart1, col_chart2 = st.columns(2)

# Paleta de colores más profesional y sobria
color_estatico = '#7f7f7f' # Gris para el estático
color_dinamico = '#1f77b4' # Azul corporativo para el dinámico

with col_chart1:
    st.markdown("### Espera Promedio por Hora", help="Muestra de manera sencilla cuántos minutos en promedio espera un camión dependiendo de la hora del día a la que llega.")
    
    # Simplificar: Agrupar por hora de llegada para que el gráfico sea muy fácil de leer
    df_static['Hora'] = (df_static['actual_arrival'] // 60).astype(int)
    if not df_static.empty:
        df_static_agg = df_static.groupby('Hora')['total_wait_time'].mean().reset_index()
        df_static_agg['scenario'] = 'Estático'
    else:
        df_static_agg = pd.DataFrame()
    
    df_dynamic['Hora'] = (df_dynamic['actual_arrival'] // 60).astype(int)
    if not df_dynamic.empty:
        df_dynamic_agg = df_dynamic.groupby('Hora')['total_wait_time'].mean().reset_index()
        df_dynamic_agg['scenario'] = 'Dinámico'
    else:
        df_dynamic_agg = pd.DataFrame()
    
    df_plot = pd.concat([df_static_agg, df_dynamic_agg])
    
    if not df_plot.empty:
        fig1 = px.line(df_plot, x='Hora', y='total_wait_time', color='scenario', markers=True,
                       labels={'Hora': 'Hora de la simulación', 'total_wait_time': 'Minutos promedio de espera'},
                       color_discrete_map={'Estático': color_estatico, 'Dinámico': color_dinamico})
        fig1.update_layout(margin=dict(l=20, r=20, t=30, b=20), legend_title_text='Modelo')
        st.plotly_chart(fig1, width='stretch')
    else:
        st.info("No hay datos suficientes para graficar.")

with col_chart2:
    st.markdown("### Productividad (Camiones por Hora)", help="Compara el rendimiento general del terminal. Un número mayor significa que el terminal atiende a los camiones de forma más ágil.")
    # Gráfico de barras
    fig2 = go.Figure(data=[
        go.Bar(name='Estático', x=['Productividad'], y=[kpis['Static']['throughput_per_hour']], marker_color=color_estatico),
        go.Bar(name='Dinámico', x=['Productividad'], y=[kpis['Dynamic']['throughput_per_hour']], marker_color=color_dinamico)
    ])
    fig2.update_layout(barmode='group', margin=dict(l=20, r=20, t=30, b=20), legend_title_text='Modelo')
    st.plotly_chart(fig2, width='stretch')

st.divider()

# Fila 3: Análisis de Causas Raíz
st.subheader("Diagnóstico de Causas Raíz", help="Este gráfico compara los minutos totales que se perdieron por cada problema. Permite ver exactamente qué solucionó el modelo Dinámico.")
st.markdown(f"""
Al comparar las ineficiencias del sistema tradicional frente al dinámico, 
podemos ver con exactitud cuántos minutos de espera totales fueron causados por cada problema particular:
""")

causes = list(rc_static.keys())
static_values = list(rc_static.values())
dynamic_values = list(rc_dynamic.values())

fig3 = go.Figure(data=[
    go.Bar(name='Estático', x=causes, y=static_values, marker_color=color_estatico, text=[f"{v/60:.1f} hrs" for v in static_values], textposition='auto'),
    go.Bar(name='Dinámico', x=causes, y=dynamic_values, marker_color=color_dinamico, text=[f"{v/60:.1f} hrs" for v in dynamic_values], textposition='auto')
])

fig3.update_layout(
    barmode='group', 
    margin=dict(l=20, r=20, t=30, b=20),
    yaxis_title="Total de Minutos de Espera Generados",
    legend_title_text='Modelo'
)
st.plotly_chart(fig3, width='stretch')
    
st.info("Nota de Eficiencia: El sistema propuesto reacciona en tiempo real a la saturación, restringiendo temporalmente nuevos accesos físicos. Esto evita la formación de colas largas en la entrada y distribuye la carga operativa a lo largo del día.")
