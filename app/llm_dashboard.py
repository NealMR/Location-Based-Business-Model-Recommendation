import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from maps_scraper import scrape_google_data
from llm_processor import generate_business_strategy_stream

st.set_page_config(page_title="AI Market Strategist", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# PREMIUM SAAS STYLING
# ==========================================
st.markdown("""
    <style>
    /* Hide Default Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Clean Global Typography */
    body, .stApp {
        background-color: #0E1117;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Typography Overrides */
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        color: #F0F6FC !important;
    }
    h2, h3 {
        font-weight: 600 !important;
        color: #C9D1D9 !important;
    }
    
    /* The Output Report Box (Premium Typography) */
    .report-box {
        background-color: #161B22;
        padding: 45px;
        border-radius: 12px;
        border: 1px solid #30363D;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.5);
        font-size: 16px;
        line-height: 1.7;
        color: #E6EDF3;
        margin-top: 20px;
    }
    
    /* Terminal Logger */
    .terminal-log {
        font-family: 'Courier New', Courier, monospace;
        background-color: #010409;
        color: #58A6FF;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #21262D;
        font-size: 14px;
        margin-bottom: 20px;
        line-height: 1.5;
    }
    </style>
""", unsafe_allow_html=True)

# State Management to Hide Map During Analysis
if 'view' not in st.session_state:
    st.session_state.view = 'map'
if 'location_name' not in st.session_state:
    st.session_state.location_name = ""

geolocator = Nominatim(user_agent="ai_location_app")

# Top Header (Always Visible)
st.markdown("<h1 style='text-align: center;'>🌍 AI Market Strategist</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8B949E; font-size: 15px;'>Memory-Tiered Edge Inference Engine</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color: #21262D;'>", unsafe_allow_html=True)

# ==========================================
# SIDEBAR: MODEL & API KEY CONFIGURATION
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Engine Configuration")
    
    # Model Selection
    model_choice = st.selectbox(
        "Select Intelligence Engine",
        ["phi3 (Local)", "qwen2.5:3b (Local)", "llama3.1 (Local)", "groq-llama-3.1-8b-instant", "gemini-1.5-flash", "gpt-4o-mini"]
    )
    
    # Strip the "(Local)" suffix for actual variable
    selected_model = model_choice.split(" ")[0]
    
    api_keys = {}
    if selected_model.startswith("groq"):
        api_keys['groq'] = st.text_input("Groq API Key", type="password")
    elif selected_model.startswith("gemini"):
        api_keys['gemini'] = st.text_input("Gemini API Key", type="password")
    elif selected_model.startswith("gpt"):
        api_keys['openai'] = st.text_input("OpenAI API Key", type="password")
        
    st.markdown("---")
    st.markdown("💡 *Local models require [Ollama](https://ollama.com/) running.*")

# ==========================================
# PHASE 1: MAP SELECTION VIEW
# ==========================================
if st.session_state.view == 'map':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_query = st.text_input("Search Location:", placeholder="e.g., Bandra West, Mumbai")
    
    map_center = [19.0760, 72.8777]
    zoom = 12
    if search_query:
        try:
            loc = geolocator.geocode(search_query)
            if loc:
                map_center = [loc.latitude, loc.longitude]
                zoom = 15
        except:
            pass

    m = folium.Map(location=map_center, zoom_start=zoom)
    folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        max_zoom=20
    ).add_to(m)
    m.add_child(folium.LatLngPopup())
    
    # Render Map Centered
    col_m1, col_m2, col_m3 = st.columns([1, 4, 1])
    with col_m2:
        st.markdown("<p style='text-align:center; color:#C9D1D9;'>Click anywhere on the map to drop a pin.</p>", unsafe_allow_html=True)
        map_data = st_folium(m, width="100%", height=500)

        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lng = map_data["last_clicked"]["lng"]
            try:
                rev_location = geolocator.reverse(f"{lat}, {lng}")
                st.session_state.location_name = rev_location.address if rev_location else f"Lat: {lat}, Lng: {lng}"
            except:
                st.session_state.location_name = f"Lat: {lat}, Lng: {lng}"
                
            st.success(f"📍 Target Selected: {st.session_state.location_name}")
            
            if st.button("🚀 Initialize Deep Analysis", type="primary", use_container_width=True):
                st.session_state.view = 'analysis'
                st.rerun()

# ==========================================
# PHASE 2: ANALYSIS & REPORT VIEW (MAP HIDDEN)
# ==========================================
elif st.session_state.view == 'analysis':
    col_a1, col_a2, col_a3 = st.columns([1, 4, 1])
    
    with col_a2:
        st.markdown(f"<h3 style='text-align:center;'>Analyzing Market: {st.session_state.location_name[:40]}...</h3>", unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        log_box = st.empty()
        
        def update_log(msg, progress):
            progress_bar.progress(progress)
            log_box.markdown(f"<div class='terminal-log'>{msg}</div>", unsafe_allow_html=True)

        # 1. Scrape
        update_log("> Spawning headless Playwright browser...<br>> Querying infrastructure and competitor data...", 20)
        
        try:
            scraped_data = scrape_google_data(st.session_state.location_name)
            infra_str = f"Schools: {scraped_data['infrastructure'].get('schools', 0)}, Colleges: {scraped_data['infrastructure'].get('colleges', 0)}"
            comp_str = "\n".join(scraped_data.get('competitors', []))
            rev_str = "\n".join(scraped_data.get('reviews', []))
            
            # 2. Process
            update_log(f"> Scraping complete.<br>> Chunking unstructured DOM data for KV-Cache...<br>> Waking {selected_model}...", 60)
            time.sleep(1)
            
            # 3. Stream Output
            update_log("> Neural synthesis initiated.<br>> Streaming report...", 90)
            
            report_container = st.empty()
            full_report = ""
            
            # Stream the report into a beautifully styled CSS box
            for chunk in generate_business_strategy_stream(st.session_state.location_name, infra_str, comp_str, rev_str, model_name=selected_model, api_keys=api_keys):
                full_report += chunk
                report_container.markdown(f"<div class='report-box'>{full_report}▌</div>", unsafe_allow_html=True)
                
            # Finalize report styling
            report_container.markdown(f"<div class='report-box'>{full_report}</div>", unsafe_allow_html=True)
            update_log("> Analysis generated successfully.<br>> Process terminated.", 100)
            
        except Exception as e:
            update_log(f"> [ERROR] Execution Failed.<br>> Details: {e}", 100)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Reset Button
        if st.button("🔄 Analyze Another Location", use_container_width=True):
            st.session_state.view = 'map'
            st.rerun()
