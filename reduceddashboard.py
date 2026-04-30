import streamlit as st
import pandas as pd
import plotly.express as px
from pvlive_api import PVLive
from datetime import datetime, timedelta, timezone

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Solar Panel Generation Output")

st.title("☀️ Solar Panel Generation Output")
st.markdown("### Near-Real-Time Data (Great Britain)")

# --- DATA FETCHING LOGIC ---
pvl = PVLive()
GMT8 = timezone(timedelta(hours=8))
@st.cache_data(ttl=1800)
def fetch_solar_data():
    # 1. Fetch National History (24 Hours)
    end_date = datetime.now(GMT8)
    start_date = end_date - timedelta(days=1)
    
    df_history = pvl.between(
        start=start_date, 
        end=end_date, 
        entity_type="pes", 
        entity_id=0, 
        dataframe=True
    )
    
    # Process history and convert to GMT+8
    df_history = df_history.rename(columns={'datetime_gmt': 'Time', 'generation_mw': 'Power'})
    #df_history['Time'] = pd.to_datetime(df_history['Time']) + timedelta(hours=8)
    
    # 2. Fetch Regional Data for the Bar Chart
    pes_map = {
        10: "East England", 11: "East Midlands", 12: "London", 13: "N. Wales/Merseyside",
        14: "North East", 15: "North West", 16: "South England", 17: "South East",
        18: "South Wales", 19: "South West", 20: "Yorkshire", 21: "South Scotland",
        22: "North Scotland", 23: "Central Scotland"
    }
    
    region_stats = []
    for pes_id, name in pes_map.items():
        try:
            reg_data = pvl.latest(entity_type="pes", entity_id=pes_id, dataframe=True)
            if not reg_data.empty:
                region_stats.append({
                    'Region': name,
                    'Power_MW': reg_data['generation_mw'].iloc[0]
                })
        except:
            continue
            
    df_regions = pd.DataFrame(region_stats)
    
    # --- CALIBRATION LOGIC ---
    # To fix the "356MW National vs 2MW Regional" issue, we distribute the National 
    # figure across the regions based on their contribution percentage.
    total_regional_sum = df_regions['Raw_Power'].sum()
    
    if total_regional_sum > 0:
        # Scale the regional values so they sum up to the National Model total
        scaling_factor = current_national / total_regional_sum
        df_regions['Power_MW'] = df_regions['Raw_Power'] * scaling_factor
    else:
        # Fallback: If regions are all 0 but National is 356, we show 0 
        # (The models are out of sync during dawn/dusk)
        df_regions['Power_MW'] = df_regions['Raw_Power']

    df_regions = df_regions.sort_values('Power_MW', ascending=False)
    
    return df_history, df_regions

# --- MAIN DASHBOARD EXECUTION ---
try:
    df_time, df_regions = fetch_solar_data()

    # --- TOP SECTION: FULL WIDTH LINE CHART ---
    fig_power = px.line(
        df_time, x='Time', y='Power', 
        title="Power Generated vs Time",
        line_shape='spline', 
        color_discrete_sequence=['#FF8C00']
    )
    st.plotly_chart(fig_power, use_container_width=True)

    # --- BOTTOM SECTION: METRIC AND BAR CHART ---
    col_metric, col_bar = st.columns([1, 3]) # Adjust ratio to match wireframe

    with col_metric:
        # Styled container for the metric
        current_val = df_time['Power'].iloc[0]
        st.subheader("Current Power")
        st.metric(label="Generated (MW)", value=f"{current_val:,.0f} MW")

    with col_bar:
        if not df_regions.empty:
            fig_bar = px.bar(
                df_regions.head(6), # Top 6 for clarity
                x='Region', 
                y='Power_MW', 
                title="Places with Highest Power Generated",
                color='Power_MW',
                color_continuous_scale='Oranges'
            )
            fig_bar.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("Regional data unavailable")

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
