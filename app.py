import streamlit as st
import pandas as pd
import os
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="F1 Universal Simulator", page_icon="🏎️", layout="wide")

# Estilo CSS corregido para visibilidad
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #E10600 !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #333333 !important; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- DEFINICIÓN DE TODOS TUS SISTEMAS ---
SISTEMAS_USUARIO = {
    "Actual (2019-2024) + FL": {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1},
    "Formato 2014 (Doble puntuación final)": {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1},
    "Formato 2010-2018 / 2025": {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1},
    "Formato 2003-2009": {1:10, 2:8, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1},
    "Formato 1991-2002": {1:10, 2:6, 3:4, 4:3, 5:2, 6:1},
    "Formato 1961-1990 (9-6-4...)": {1:9, 2:6, 3:4, 4:3, 5:2, 6:1},
    "Formato 1960 (8-6-4...)": {1:8, 2:6, 3:4, 4:3, 5:2, 6:1},
    "Formato 1950-1959": {1:8, 2:6, 3:4, 4:3, 5:2}
}

st.title("🏎️ F1 Universal Simulator: Todos los Sistemas Históricos")

# --- CARGA DE DATOS ---
nombre_archivo = '2007_data.csv'

@st.cache_data
def cargar_datos():
    if os.path.exists(nombre_archivo):
        try:
            df = pd.read_csv(nombre_archivo, sep=None, engine='python', encoding='latin-1')
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"Error: {e}")
    return None

df = cargar_datos()

if df is not None:
    # --- SIDEBAR: SELECCIÓN DE TU SISTEMA ---
    st.sidebar.header("📜 Sistemas Históricos")
    nombre_sistema = st.sidebar.selectbox("Elige el sistema de tu Excel:", list(SISTEMAS_USUARIO.keys()))
    
    # Obtener el mapa de puntos elegido
    puntos_map = SISTEMAS_USUARIO[nombre_sistema]
    
    # Vuelta rápida (FL) automática o manual
    if "2019-2024" in nombre_sistema:
        st.sidebar.info("Este sistema incluye +1 punto por Vuelta Rápida (Top 10).")
        puntos_fl = 1
    elif "1950-1959" in nombre_sistema:
        st.sidebar.info("En esta época se solía dar +1 por VR a cualquier posición.")
        puntos_fl = 1
    else:
        puntos_fl = st.sidebar.slider("Puntos extra por Vuelta Rápida", 0, 5, 0)

    # --- LÓGICA DE PROCESAMIENTO ---
    def procesar_todo():
        columnas_pos = [c for c in df.columns if c.endswith('_POS')]
        lista_gps = [c.replace('_POS', '') for c in columnas_pos]
        
        registros = []
        for _, row in df.iterrows():
            piloto = row['PILOTO']
            for i, gp in enumerate(lista_gps):
                pos_val = str(row[f"{gp}_POS"]).strip()
                pts = 0
                if pos_val.isdigit():
                    pos_int = int(pos_val)
                    pts = puntos_map.get(pos_int, 0)
                    
                    # Caso especial Formato 2014 (Doble puntos en la última carrera BRA)
                    if nombre_sistema == "Formato 2014 (Doble puntuación final)" and gp == "BRA":
                        pts *= 2
                    
                    # Vuelta rápida
                    if str(row.get(f"{gp}_FL", "")).strip() == '1':
                        # En sistemas modernos, solo si queda en el Top 10
                        if "Actual" in nombre_sistema or "2010" in nombre_sistema:
                            if pos_int <= 10: pts += puntos_fl
                        else:
                            pts += puntos_fl # En sistemas antiguos se daba a cualquiera
                
                equipo = str(row.get(f"{gp}_TEAM", "Sin Equipo")).strip()
                registros.append({"Piloto": piloto, "Equipo": equipo, "GP": gp, "Puntos": pts, "Orden": i})
        
        df_base = pd.DataFrame(registros)
        df_base = df_base.sort_values(['Piloto', 'Orden'])
        df_base['Acumulado_P'] = df_base.groupby('Piloto')['Puntos'].cumsum()
        
        rank_p = df_base.groupby('Piloto')['Puntos'].sum().reset_index().sort_values("Puntos", ascending=False)
        rank_e = df_base.groupby('Equipo')['Puntos'].sum().reset_index().sort_values("Puntos", ascending=False)
        
        df_e_prog = df_base.groupby(['Equipo', 'GP', 'Orden'])['Puntos'].sum().reset_index()
        df_e_prog = df_e_prog.sort_values(['Equipo', 'Orden'])
        df_e_prog['Acumulado_E'] = df_e_prog.groupby('Equipo')['Puntos'].cumsum()

        return rank_p, rank_e, df_base, df_e_prog

    df_rank_p, df_rank_e, df_p_prog, df_e_prog = procesar_todo()

    # --- PANEL DE RESULTADOS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🥇 Ganador", df_rank_p.iloc[0]['Piloto'])
    col2.metric("🥈 Segundo", df_rank_p.iloc[1]['Piloto'])
    ventaja = int(df_rank_p.iloc[0]['Puntos'] - df_rank_p.iloc[1]['Puntos'])
    col3.metric("📏 Diferencia", f"{ventaja} Pts")

    t_pilotos, t_equipos = st.tabs(["🏆 Pilotos", "🏭 Equipos"])

    with t_pilotos:
        st.subheader(f"Mundial bajo el {nombre_sistema}")
        st.table(df_rank_p.head(15))
        
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            st.plotly_chart(px.bar(df_rank_p.head(10), x='Piloto', y='Puntos', color='Puntos', color_continuous_scale='Reds'), use_container_width=True)
        with c_p2:
            top5 = df_rank_p.head(5)['Piloto'].tolist()
            st.plotly_chart(px.line(df_p_prog[df_p_prog['Piloto'].isin(top5)], x='GP', y='Acumulado_P', color='Piloto', markers=True), use_container_width=True)

    with t_equipos:
        st.subheader("Mundial de Constructores")
        st.table(df_rank_e)
        st.plotly_chart(px.line(df_e_prog, x='GP', y='Acumulado_E', color='Equipo', markers=True), use_container_width=True)

else:
    st.error("No se encuentra '2007_data.csv'")