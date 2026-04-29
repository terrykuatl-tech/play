import streamlit as st
import pandas as pd
import plotly.express as px

# Dashboard Configuration
st.set_page_config(layout="wide", page_title="Solar Generation Dashboard")
st.title("Solar Panel Generation Output (Europe)")

# --- MOCK DATA LOADING (Replace with OPSD CSV/API) ---
# In a real app, use pd.read_csv("https://data.open-power-system-data.org/...")
df_time = pd.DataFrame({
    'Time': pd.date_range(start='2024-01-01', periods=24, freq='H'),
    'Irradiance': [100, 150, 300, 600, 800, 950, 1000, 900, 700, 400, 200, 50] * 2,
    'Power': [10, 25, 60, 120, 180, 210, 230, 200, 150, 80, 40, 10] * 2
})

df_geo = pd.DataFrame({
    'Country': ['Spain', 'Italy', 'Greece', 'Portugal', 'Germany', 'France'],
    'Intensity': [950, 890, 870, 840, 550, 610]
}).sort_values('Intensity', ascending=False)

# --- DASHBOARD LAYOUT ---

# Top Row: Two Line Charts
col1, col2 = st.columns(2)

with col1:
    fig_light = px.line(df_time, x='Time', y='Irradiance', 
                        title="Line chart (Light intensity vs time)")
    st.plotly_chart(fig_light, use_container_width=True)

with col2:
    fig_power = px.line(df_time, x='Time', y='Power', 
                        title="Line chart (Power Generated vs time)",
                        line_shape='spline', color_discrete_sequence=['orange'])
    st.plotly_chart(fig_power, use_container_width=True)

# Bottom Row: Metrics and Bar Chart
col3, col4, col5 = st.columns([1, 1, 2])

with col3:
    st.subheader("Current Intensity")
    st.metric(label="W/m²", value=f"{df_time['Irradiance'].iloc[-1]}")

with col4:
    st.subheader("Current Power Generated")
    st.metric(label="MW", value=f"{df_time['Power'].iloc[-1]}")

with col5:
    fig_bar = px.bar(df_geo, x='Country', y='Intensity', 
                     title="Bar chart - Places with highest light intensity",
                     color='Intensity', color_continuous_scale='Viridis')
    st.plotly_chart(fig_bar, use_container_width=True)