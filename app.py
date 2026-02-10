import streamlit as st
import pandas as pd
import os
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="F1 Universal Simulator", page_icon="🏎️", layout="wide")

# 2. Estilo CSS para métricas
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #333333 !important; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 3. Colores F1
COLORES_F1 = {
    'Ferrari': '#FF0000', 'McLaren': '#C0C0C0', 'BMW Sauber': '#000080',
    'Renault': '#FFF500', 'Williams': '#005AFF', 'Red Bull': '#00008F',
    'Toyota': '#E4002B', 'Toro Rosso': '#0000FF', 'Honda': '#008000',
    'Super Aguri': '#FF0000', 'Spyker': '#FF8700', 'Sin Equipo': '#808080'
}

# 4. Sistemas de Puntos
SISTEMAS_USUARIO = {
    "Formato 2010-2018 / 2025-2026": {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1},
    "Formato 2019-2024": {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1},
    "Formato 2014 (Doble puntuación final)": {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1},
    "Formato 2003-2009": {1:10, 2:8, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1},
    "Formato 1991-2002": {1:10, 2:6, 3:4, 4:3, 5:2, 6:1},
    "Formato 1961-1990": {1:9, 2:6, 3:4, 4:3, 5:2, 6:1},
    "Formato 1960": {1:8, 2:6, 3:4, 4:3, 5:2, 6:1},
    "Formato 1950-1959": {1:8, 2:6, 3:4, 4:3, 5:2}
}

st.title("🏎️ F1 Universal Simulator: Todos los Sistemas Históricos")

nombre_archivo = '2007_data.csv'

@st.cache_data
def cargar_datos():
    if os.path.exists(nombre_archivo):
        try:
            df = pd.read_csv(nombre_archivo, sep=None, engine='python', encoding='latin-1')
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"Error cargando el CSV: {e}")
    return None

df = cargar_datos()

if df is not None:
    # --- PANEL DE CONFIGURACIÓN (INTERFAZ) ---
    with st.container():
        st.markdown("### ⚙️ Panel de Configuración")
        col_sys, col_fl = st.columns([2, 1])
        
        with col_sys:
            nombre_sistema = st.selectbox(
                "Selecciona el sistema de puntuación histórico:", 
                list(SISTEMAS_USUARIO.keys())
            )
            puntos_map = SISTEMAS_USUARIO[nombre_sistema]

        with col_fl:
            # Aquí solo definimos CUÁNTOS puntos vale la vuelta rápida
            if "2019-2024" in nombre_sistema or "1950-1959" in nombre_sistema:
                st.info("💡 +1 punto por Vuelta Rápida incluido.")
                puntos_fl = 1
            else:
                puntos_fl = st.number_input("Puntos extra por Vuelta Rápida:", 0, 5, 0)
        st.divider()

    # --- PROCESAMIENTO (LÓGICA) ---
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
                    
                    # Regla 2014
                    if nombre_sistema == "Formato 2014 (Doble puntuación final)" and gp == "BRA":
                        pts *= 2
                    
                    # Lógica de Vuelta Rápida (Aquí es donde debe ir)
                    if str(row.get(f"{gp}_FL", "")).strip() == '1':
                        if "2019-2024" in nombre_sistema or "2010" in nombre_sistema:
                            if pos_int <= 10: pts += puntos_fl
                        else:
                            pts += puntos_fl
                
                equipo = str(row.get(f"{gp}_TEAM", "Sin Equipo")).strip()
                registros.append({"Piloto": piloto, "Equipo": equipo, "GP": gp, "Puntos": pts, "Orden": i})
        
        df_base = pd.DataFrame(registros)
        
        # Desempate FIA
        conteo_posiciones = []
        for piloto in df_base['Piloto'].unique():
            fila_piloto = df['PILOTO'] == piloto
            counts = {'Piloto': piloto}
            for p in range(1, 21):
                counts[f'P{p}'] = (df[fila_piloto][[c for c in df.columns if c.endswith('_POS')]] == str(p)).sum().sum()
            conteo_posiciones.append(counts)
        
        df_desempate = pd.DataFrame(conteo_posiciones)
        rank_p = df_base.groupby('Piloto')['Puntos'].sum().reset_index()
        rank_p = rank_p.merge(df_desempate, on='Piloto')
        
        columnas_orden = ['Puntos'] + [f'P{i}' for i in range(1, 21)]
        rank_p = rank_p.sort_values(by=columnas_orden, ascending=False).reset_index(drop=True)
        
        rank_e = df_base.groupby('Equipo')['Puntos'].sum().reset_index().sort_values("Puntos", ascending=False)
        
        df_base = df_base.sort_values(['Piloto', 'Orden'])
        df_base['Acumulado_P'] = df_base.groupby('Piloto')['Puntos'].cumsum()
        
        df_e_prog = df_base.groupby(['Equipo', 'GP', 'Orden'])['Puntos'].sum().reset_index()
        df_e_prog = df_e_prog.sort_values(['Equipo', 'Orden'])
        df_e_prog['Acumulado_E'] = df_e_prog.groupby('Equipo')['Puntos'].cumsum()

        colores_pilotos = {f['Piloto']: COLORES_F1.get(f['Equipo'], '#808080') for _, f in df_base.iterrows()}

        return rank_p, rank_e, df_base, df_e_prog, colores_pilotos

    df_rank_p, df_rank_e, df_p_prog, df_e_prog, colores_pilotos = procesar_todo()

    # --- MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🥇 Campeón", df_rank_p.iloc[0]['Piloto'])
    col2.metric("🥈 Subcampeón", df_rank_p.iloc[1]['Piloto'])
    ventaja = int(df_rank_p.iloc[0]['Puntos'] - df_rank_p.iloc[1]['Puntos'])
    col3.metric("📏 Diferencia", f"{ventaja} Pts")

    # --- TABS ---
    t_pilotos, t_equipos = st.tabs(["🏆 Mundial de Pilotos", "🏭 Mundial de Equipos"])

    with t_pilotos:
        st.subheader(f"Clasificación Final - {nombre_sistema}")
        with st.dataframe(df_rank_p[['Piloto', 'Puntos']].head(15), use_container_width=True, hide_index=True): pass
        
        cp1, cp2 = st.columns(2)
        with cp1:
            st.plotly_chart(px.bar(df_rank_p.head(10), x='Piloto', y='Puntos', color='Piloto', color_discrete_map=colores_pilotos, title="Top 10 Puntos"), use_container_width=True)
        with cp2:
            top5 = df_rank_p.head(5)['Piloto'].tolist()
            st.plotly_chart(px.line(df_p_prog[df_p_prog['Piloto'].isin(top5)], x='GP', y='Acumulado_P', color='Piloto', color_discrete_map=colores_pilotos, markers=True, title="Evolución del Título"), use_container_width=True)

    with t_equipos:
        st.subheader("Clasificación de Constructores")
        st.table(df_rank_e)
        st.plotly_chart(px.line(df_e_prog, x='GP', y='Acumulado_E', color='Equipo', color_discrete_map=COLORES_F1, markers=True, title="Progreso Equipos"), use_container_width=True)
else:
    st.error("⚠️ Archivo no encontrado.")