import streamlit as st
import pandas as pd
import plotly.express as px
from pvlive_api import PVLive
from datetime import datetime, timedelta

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Live Solar Intensity Dashboard")

# Custom CSS to improve UI spacing
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_index=True)

st.title("☀️ Solar Generation & Light Intensity Dashboard")
st.markdown("### Near-Real-Time Data (Great Britain)")

# --- DATA FETCHING LOGIC ---
pvl = PVLive()

@st.cache_data(ttl=1800) # Cache for 30 minutes to match PV_Live refresh cycle
def fetch_solar_data():
    # 1. Fetch National History (24 Hours)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    df_history = pvl.between(
        start=start_date, 
        end=end_date, 
        entity_type="pes", 
        entity_id=0, # 0 = National
        extra_fields="installedcapacity_mwp",
        dataframe=True
    )
    
    # Process history
    df_history = df_history.rename(columns={'datetime_gmt': 'Time', 'generation_mw': 'Power'})
    df_history['Utilization_%'] = (df_history['Power'] / df_history['installedcapacity_mwp']) * 100
    
    # 2. Fetch and Rank Regional Intensity Proxy (Top 4)
    pes_map = {
        10: "East England", 11: "East Midlands", 12: "London", 13: "N. Wales/Merseyside",
        14: "North East", 15: "North West", 16: "South England", 17: "South East",
        18: "South Wales", 19: "South West", 20: "Yorkshire", 21: "South Scotland",
        22: "North Scotland", 23: "Central Scotland"
    }
    
    region_stats = []
    for pes_id, name in pes_map.items():
        try:
            reg_data = pvl.latest(entity_type="pes", entity_id=pes_id, extra_fields="installedcapacity_mwp", dataframe=True)
            reg_data['Region_Name'] = name
            # Intensity Proxy calculation
            reg_data['Intensity_Proxy'] = (reg_data['generation_mw'] / reg_data['installedcapacity_mwp']) * 100
            region_stats.append(reg_data)
        except Exception:
            continue
            
    df_all_regions = pd.concat(region_stats)
    df_top_4 = df_all_regions.sort_values('Intensity_Proxy', ascending=False).head(4)
    
    return df_history, df_top_4

# --- EXECUTION ---
try:
    df_time, df_top_4 = fetch_solar_data()

    # --- TOP ROW: LINE CHARTS ---
    col1, col2 = st.columns(2)

    with col1:
        fig_light = px.line(
            df_time, x='Time', y='Utilization_%', 
            title="Light Intensity Proxy (Capacity Utilization %)",
            labels={'Utilization_%': 'Intensity (%)'},
            color_discrete_sequence=['#FFD700'] # Gold/Sun color
        )
        fig_light.update_layout(hovermode="x unified")
        st.plotly_chart(fig_light, use_container_width=True)

    with col2:
        fig_power = px.line(
            df_time, x='Time', y='Power', 
            title="Power Generated (MW) - Last 24 Hours",
            labels={'Power': 'Generation (MW)'},
            line_shape='spline', 
            color_discrete_sequence=['#FF8C00'] # Orange color
        )
        fig_power.update_layout(hovermode="x unified")
        st.plotly_chart(fig_power, use_container_width=True)

    st.divider()

    # --- BOTTOM ROW: METRICS & BAR CHART ---
    col3, col4, col5 = st.columns([1, 1, 2])

    with col3:
        current_intensity = df_time['Utilization_%'].iloc[0]
        st.metric(
            label="Current Intensity Proxy", 
            value=f"{current_intensity:.2f}%",
            help="Higher percentage indicates higher solar irradiance relative to capacity."
        )

    with col4:
        current_power = df_time['Power'].iloc[0]
        st.metric(
            label="Current Power Output", 
            value=f"{current_power:,.0f} MW"
        )

    with col5:
        fig_bar = px.bar(
            df_top_4, 
            x='Region_Name', 
            y='Intensity_Proxy', 
            title="Top 4 Regions with Highest Light Intensity",
            labels={'Intensity_Proxy': 'Intensity %', 'Region_Name': 'Region'},
            color='Intensity_Proxy', 
            color_continuous_scale='YlOrRd' # Yellow to Red scale
        )
        # Hide the color bar for a cleaner look if desired
        fig_bar.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)

except Exception as e:
    st.error("Failed to connect to PV_Live API.")
    st.write(f"Technical details: {e}")
    st.info("Check your requirements.txt for 'pvlive-api' and 'pandas'.")

# --- FOOTER ---
st.caption("Data source: Sheffield Solar PV_Live API. Intensity Proxy is calculated as (Actual Generation / Installed Capacity).")
