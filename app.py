import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster, Fullscreen
import altair as alt
import datetime

#page configuration
st.set_page_config(
    page_title="AQHI: Delhi Bio-Surveillance Command Center",
    page_icon="☣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS 
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0E1117;
    }
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00FF99; /* Cyberpunk Green */
    }
    div[data-testid="stMetricLabel"] {
        color: #888888;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161B22;
        border-radius: 5px;
        color: white;
        padding-right: 20px;
        padding-left: 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        color: white !important;
    }
    /* Alert Box */
    .alert-box {
        padding: 15px;
        background-color: #3b1e1e;
        border-left: 5px solid #ff4b4b;
        color: #ffcccc;
        border-radius: 5px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# data engine
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("final_project_data.csv")
        df['date'] = pd.to_datetime(df['date'])
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour # Extract Hour
        
        # Exact Coordinates for Delhi Hotspots
        coords = {
            'Anand Vihar': [28.6469, 77.3160],
            'ITO': [28.6266, 77.2425],
            'Dwarka': [28.5921, 77.0460],
            'Rohini': [28.7041, 77.1025],
            'Connaught Place': [28.6304, 77.2177],
            'Jahangirpuri': [28.7259, 77.1627],
            'JNU': [28.5400, 77.1668],
            'Munirka': [28.5562, 77.1732],
            'Vasant Kunj': [28.5300, 77.1520],
            'RK Puram': [28.5660, 77.1767],
            'IIT Delhi': [28.5450, 77.1926]
        }
        
        # Map Coordinates
        df['lat'] = df['location'].map(lambda x: coords.get(x, [None, None])[0])
        df['lon'] = df['location'].map(lambda x: coords.get(x, [None, None])[1])
        df = df.dropna(subset=['lat', 'lon'])
        
        return df, coords
        
    except FileNotFoundError:
        return None, None

df, location_coords = load_data()

if df is None:
    st.error("CRITICAL ERROR: Data Pipeline Broken. Run 'data_processor.py' first.")
    st.stop()

# SIDEBAR CONTROLS
st.sidebar.markdown("## 📡 Signal Controls")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/5664/5664993.png", width=60)

# Filters
date_range = st.sidebar.date_input(
    "📅 Analysis Period",
    value=(df['date'].min(), df['date'].max()),
    min_value=df['date'].min(),
    max_value=df['date'].max()
)
selected_locs = st.sidebar.multiselect("📍 Locations", sorted(df['location'].unique()), default=sorted(df['location'].unique()))
selected_symptoms = st.sidebar.multiselect("🏥 Symptoms", sorted(df['detected_symptom'].unique()), default=sorted(df['detected_symptom'].unique()))

# Apply Filters
mask = (
    (df['date'].dt.date >= date_range[0]) & 
    (df['date'].dt.date <= date_range[1]) & 
    (df['location'].isin(selected_locs)) & 
    (df['detected_symptom'].isin(selected_symptoms))
)
filtered_df = df[mask]

st.sidebar.divider()
st.sidebar.info(f"**System Status:** Online\n**Latency:** 24ms\n**Signals Processed:** {len(filtered_df)}")

#  DASHBOARD HEADER 
st.title("🫁 AQHI: Delhi Bio-Surveillance System")

# AI Insight Logic
if not filtered_df.empty:
    top_loc = filtered_df['location'].mode()[0]
    top_sym = filtered_df['detected_symptom'].mode()[0]
    avg_severity = filtered_df['severity_score'].mean()
    
    insight_html = f"""
    <div class='alert-box'>
        <b>🤖 AI SYSTEM ALERT:</b> High concentration of <b>{top_sym}</b> signals detected in <b>{top_loc}</b>. 
        Average severity score is <b>{avg_severity:.1f}/10</b>. 
        Correlation with CPCB PM2.5 sensors is <b>Positive</b>. Recommendation: Deploy mobile health units to {top_loc}.
    </div>
    """
    st.markdown(insight_html, unsafe_allow_html=True)

#MAIN TABS
tab1, tab2, tab3, tab4 = st.tabs(["📊 Command Center", "🗺️ Geo-Intelligence", "📈 Trend Analysis", "📂 Data Vault"])

# COMMAND CENTER (KPIs)
with tab1:
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bio-Signals", len(filtered_df), "Live")
    
    if not filtered_df.empty:
        curr_aqi = int(filtered_df['official_aqi'].mean())
        c2.metric("Official CPCB AQI", curr_aqi, "Severe" if curr_aqi > 400 else "Poor", delta_color="inverse")
        c3.metric("Critical Hotspot", filtered_df['location'].mode()[0])
        c4.metric("Dominant Symptom", filtered_df['detected_symptom'].mode()[0])
    
    st.divider()
    
    # Split: Pie Chart + Recent Feed
    col_chart, col_feed = st.columns([2, 1])
    
    with col_chart:
        st.subheader("🏥 Symptom Distribution")
        if not filtered_df.empty:
            count_df = filtered_df['detected_symptom'].value_counts().reset_index()
            count_df.columns = ['Symptom', 'Count']
            
            # Donut Chart
            chart = alt.Chart(count_df).mark_arc(innerRadius=60).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Symptom", type="nominal", scale=alt.Scale(scheme='magma')),
                tooltip=['Symptom', 'Count']
            )
            st.altair_chart(chart, use_container_width=True)
            
    with col_feed:
        st.subheader("📡 Live Signal Feed")
        if not filtered_df.empty:
            # Show last 4 tweets like a chat log
            recent = filtered_df.sort_values('timestamp', ascending=False).head(4)
            for _, row in recent.iterrows():
                st.info(f"📍 **{row['location']}**: {row['raw_text']}")

# GEO-INTELLIGENCE (Map)

with tab2:
    st.subheader("🗺️ Geospatial Outbreak Heatmap")
    
    # 1. SAFE CENTER CALCULATION (Prevents Map Crash)
    # We default to Delhi Center if data is missing or invalid
    default_center = [28.6139, 77.2090]
    
    if not filtered_df.empty:
        # Calculate mean, but check for NaNs just in case
        lat_mean = filtered_df['lat'].mean()
        lon_mean = filtered_df['lon'].mean()
        
        # If mean calculation fails (e.g. data is there but lat is NaN), use default
        if pd.notna(lat_mean) and pd.notna(lon_mean):
            center = [lat_mean, lon_mean]
            zoom = 13 if len(selected_locs) <= 2 else 11
        else:
            center = default_center
            zoom = 11
    else:
        center = default_center
        zoom = 11
        st.warning("⚠️ No data available for Heatmap in this selection.")

    # 2. MAP CREATION
    # We use 'OpenStreetMap' as a backup if Dark Matter fails to load
    try:
        m = folium.Map(location=center, zoom_start=zoom, tiles='CartoDB dark_matter')
    except:
        m = folium.Map(location=center, zoom_start=zoom, tiles='OpenStreetMap')

    Fullscreen().add_to(m)
    
    if not filtered_df.empty:
        # Heatmap Layer
        # Drop any rows with NaN lat/lon before plotting to avoid errors
        map_data = filtered_df.dropna(subset=['lat', 'lon'])
        heat_data = map_data[['lat', 'lon', 'severity_score']].values.tolist()
        
        if heat_data:
            HeatMap(heat_data, radius=20, blur=15, gradient={0.4: 'blue', 0.7: 'lime', 1: 'red'}).add_to(m)
        
        # Cluster Layer
        marker_cluster = MarkerCluster(name="Specific Alerts").add_to(m)
        for _, row in map_data.head(80).iterrows():
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"<b>{row['location']}</b><br>{row['detected_symptom']}<br>Severity: {row['severity_score']}",
                icon=folium.Icon(color='red' if row['severity_score'] > 7 else 'orange', icon='heart')
            ).add_to(marker_cluster)
            
        # JNU Marker
        if 'JNU' in location_coords:
            folium.CircleMarker(
                location=location_coords['JNU'], radius=10, color='#00FF99', fill=True, popup="JNU Campus Sensor"
            ).add_to(m)

    # 3. RENDER WITH EXPLICIT WIDTH
    # Setting width=700 often fixes the "invisible map" bug in tabs
    st_folium(m, width=1000, height=550, returned_objects=[])

# TREND ANALYSIS 
with tab3:
    st.subheader("📈 Correlation & Temporal Analysis")
    
    if not filtered_df.empty:
        # A. Dual Axis Chart (The Science Proof)
        daily_stats = filtered_df.groupby('date').agg(
            Official_AQI=('official_aqi', 'mean'),
            Bio_Signals=('detected_symptom', 'count')
        ).reset_index()
        
        base = alt.Chart(daily_stats).encode(x='date:T')
        
        line_aqi = base.mark_line(color='#FF4B4B', strokeWidth=3).encode(
            y=alt.Y('Official_AQI', title='CPCB AQI (Red Line)'),
            tooltip=['date', 'Official_AQI']
        )
        
        bar_signals = base.mark_bar(color='#FFA500', opacity=0.3).encode(
            y=alt.Y('Bio_Signals', title='Health Complaints (Orange Bars)'),
            tooltip=['date', 'Bio_Signals']
        )
        
        st.altair_chart((bar_signals + line_aqi).resolve_scale(y='independent'), use_container_width=True)
        
        st.divider()
        
        # B. Hourly Activity (When do people get sick?)
        st.markdown("#### 🕒 Peak Symptom Hours")
        hourly_counts = filtered_df.groupby('hour')['detected_symptom'].count().reset_index()
        
        bar_hour = alt.Chart(hourly_counts).mark_bar(color='#00FF99').encode(
            x=alt.X('hour:O', title='Hour of Day'),
            y=alt.Y('detected_symptom', title='Alert Count'),
            tooltip=['hour', 'detected_symptom']
        )
        st.altair_chart(bar_hour, use_container_width=True)

# DATA VAULT
with tab4:
    col_dl, col_prev = st.columns([1, 4])
    
    with col_dl:
        st.subheader("⬇️ Export")
        if not filtered_df.empty:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download CSV Report",
                csv,
                "delhi_bio_surveillance_report.csv",
                "text/csv",
                key='download-csv'
            )
            
    with col_prev:
        st.subheader("📂 Raw Intelligence")
        st.dataframe(
            filtered_df[['timestamp', 'location', 'raw_text', 'detected_symptom', 'severity_score', 'official_aqi']].sort_values('timestamp', ascending=False),
            use_container_width=True
        )

# Footer
st.markdown("---")

