import streamlit as st
import pandas as pd
import plotly.express as px
from pvlive_api import PVLive
from datetime import datetime, timedelta, timezone

# --- DASHBOARD CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Live Solar Intensity Dashboard")

st.title("☀️ Solar Generation & Light Intensity Dashboard")
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
        extra_fields="installedcapacity_mwp",
        dataframe=True
    )
    
    # Process history and handle potential missing capacity data
    df_history = df_history.rename(columns={'datetime_gmt': 'Time', 'generation_mw': 'Power'})
    
    # Use .get() to avoid KeyError if the extra_field didn't return correctly
    cap_col = 'installedcapacity_mwp'
    if cap_col in df_history.columns:
        # Fill zeros or NaNs to avoid division errors
        df_history[cap_col] = df_history[cap_col].replace(0, pd.NA).ffill()
        df_history['Utilization_%'] = (df_history['Power'] / df_history[cap_col]) * 100
    else:
        df_history['Utilization_%'] = 0
    
    # 2. Rank All Regions and Get Top 4
    pes_map = {
        10: "East England", 11: "East Midlands", 12: "London", 13: "N. Wales/Merseyside",
        14: "North East", 15: "North West", 16: "South England", 17: "South East",
        18: "South Wales", 19: "South West", 20: "Yorkshire", 21: "South Scotland",
        22: "North Scotland", 23: "Central Scotland"
    }
    
    region_stats = []
    for pes_id, name in pes_map.items():
        try:
            # Note: extra_fields is a comma-separated string for the API
            reg_data = pvl.latest(entity_type="pes", entity_id=pes_id, extra_fields="installedcapacity_mwp", dataframe=True)
            if not reg_data.empty and cap_col in reg_data.columns:
                capacity = reg_data[cap_col].iloc[0]
                generation = reg_data['generation_mw'].iloc[0]
                
                # Guard against zero capacity
                intensity = (generation / capacity * 100) if capacity > 0 else 0
                
                region_stats.append({
                    'Region_Name': name,
                    'Intensity_Proxy': intensity,
                    'Power_MW': generation
                })
        except Exception:
            continue
            
    df_top_4 = pd.DataFrame(region_stats).sort_values('Intensity_Proxy', ascending=False).head(4)
    
    return df_history, df_top_4

# --- MAIN DASHBOARD EXECUTION ---
try:
    df_time, df_top_4 = fetch_solar_data()

    # --- TOP ROW: LINE CHARTS ---
    col1, col2 = st.columns(2)

    with col1:
        fig_light = px.line(
            df_time, x='Time', y='Utilization_%', 
            title="Capacity Utilization %",
            labels={'Utilization_%': 'Utilisation (%)'},
            color_discrete_sequence=['#FFD700']
        )
        st.plotly_chart(fig_light, use_container_width=True)

    with col2:
        fig_power = px.line(
            df_time, x='Time', y='Power', 
            title="Power Generated (MW) - Last 24 Hours",
            line_shape='spline', 
            color_discrete_sequence=['#FF8C00']
        )
        st.plotly_chart(fig_power, use_container_width=True)

    st.divider()

    # --- BOTTOM ROW: METRICS & BAR CHART ---
    col3, col4, col5 = st.columns([1, 1, 2])

    with col3:
        # Get the most recent value (first row in PV_Live dataframe)
        current_intensity = df_time['Utilization_%'].iloc[0]
        st.metric(label="Current Intensity Proxy", value=f"{current_intensity:.2f}%")

    with col4:
        current_power = df_time['Power'].iloc[0]
        st.metric(label="Current Power Output", value=f"{current_power:,.0f} MW")

    with col5:
        if not df_top_4.empty:
            fig_bar = px.bar(
                df_top_4, x='Region_Name', y='Utilization', 
                title="Top 4 Regions by Utilisation",
                color='Intensity_Proxy', color_continuous_scale='YlOrRd'
            )
            fig_bar.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("No regional data available.")

except Exception as e:
    st.error(f"Critical Error: {e}")
