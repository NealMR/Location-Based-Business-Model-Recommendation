import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import plotly.graph_objects as go
import streamlit.components.v1 as components
import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Ensure Playwright browser is installed in cloud environments
os.system("playwright install chromium")

from maps_scraper import scrape_google_data
from llm_processor import generate_business_strategy_stream, chat_with_report

st.set_page_config(page_title="AI Market Strategist", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# PREMIUM SAAS STYLING
# ==========================================
st.markdown("""
    <style>
    /* Hide Default Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
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

# Top Header
st.markdown("<h1 style='text-align: center;'>AI Market Strategist</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8B949E; font-size: 15px;'>Memory-Tiered Edge Inference Engine</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color: #21262D;'>", unsafe_allow_html=True)

# ==========================================
# SIDEBAR: MODEL & API KEY CONFIGURATION
# ==========================================
with st.sidebar:
    st.markdown("### Engine Configuration")
    
    model_choice = st.selectbox(
        "Select Intelligence Engine",
        [
            "phi3 (Local)", 
            "qwen2.5:3b (Local)", 
            "llama3.1 (Local)", 
            "groq-openai/gpt-oss-120b", 
            "groq-openai/gpt-oss-20b", 
            "gemini-1.5-flash", 
            "gpt-4o-mini"
        ]
    )
    
    selected_model = model_choice.split(" ")[0]
    
    api_keys = {}
    if selected_model.startswith("groq"):
        api_keys['groq'] = st.text_input("Groq API Key", type="password")
    elif selected_model.startswith("gemini"):
        api_keys['gemini'] = st.text_input("Gemini API Key", type="password")
    elif selected_model.startswith("gpt"):
        api_keys['openai'] = st.text_input("OpenAI API Key", type="password")
        
    st.markdown("---")
    st.markdown("*Note: Local models require [Ollama](https://ollama.com/) running.*")

# ==========================================
# PHASE 1: MAP SELECTION VIEW
# ==========================================
if st.session_state.view == 'map':
    st.markdown("<h3 style='text-align:center;'>Location Targeting</h3>", unsafe_allow_html=True)
    col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
    with col_m2:
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
    
    col_map1, col_map2, col_map3 = st.columns([1, 4, 1])
    with col_map2:
        st.markdown("<p style='text-align:center; color:#8B949E; font-size:14px;'>Click anywhere on the map to drop a pin.</p>", unsafe_allow_html=True)
        map_data = st_folium(m, width="100%", height=500)

        if map_data and map_data.get("last_clicked"):
            lat = map_data["last_clicked"]["lat"]
            lng = map_data["last_clicked"]["lng"]
            try:
                rev_location = geolocator.reverse(f"{lat}, {lng}")
                st.session_state.location_name = rev_location.address if rev_location else f"Lat: {lat}, Lng: {lng}"
            except:
                st.session_state.location_name = f"Lat: {lat}, Lng: {lng}"
                
            st.success(f"Target Selected: {st.session_state.location_name}")
            
            if st.button("Initialize Deep Analysis", type="primary", use_container_width=True):
                st.session_state.view = 'analysis'
                st.rerun()

# ==========================================
# PHASE 2: ANALYSIS & REPORT VIEW (MAP HIDDEN)
# ==========================================
elif st.session_state.view == 'analysis':
    st.markdown("### Strategic Intelligence Report")
    
    progress_bar = st.progress(0)
    log_box = st.empty()
    
    def update_log(msg, progress):
        progress_bar.progress(progress)
        log_box.markdown(f"<div class='terminal-log'>{msg}</div>", unsafe_allow_html=True)

    # Validate API Keys
    if selected_model.startswith('groq') and not api_keys.get('groq'):
        update_log("> [ERROR] Missing Groq API Key! Please enter it in the sidebar and press Enter.", 0)
        st.stop()
    elif selected_model.startswith('gemini') and not api_keys.get('gemini'):
        update_log("> [ERROR] Missing Gemini API Key! Please enter it in the sidebar and press Enter.", 0)
        st.stop()
    elif selected_model.startswith('gpt') and not api_keys.get('openai'):
        update_log("> [ERROR] Missing OpenAI API Key! Please enter it in the sidebar and press Enter.", 0)
        st.stop()

    try:
        if "generated_report" not in st.session_state:
            scraped_data = scrape_google_data(st.session_state.location_name)
            infra_str = f"Schools: {scraped_data['infrastructure'].get('schools', 0)}, Colleges: {scraped_data['infrastructure'].get('colleges', 0)}"
            comp_str = "\n".join(scraped_data.get('competitors', []))
            rev_str = "\n".join(scraped_data.get('reviews', []))
            
            # Store visualization data
            st.session_state.infra_data = scraped_data.get('infrastructure', {})
            st.session_state.comp_count = len(scraped_data.get('competitors', []))
            st.session_state.rev_count = len(scraped_data.get('reviews', []))
            
            update_log(f"> Scraping complete.<br>> Chunking unstructured DOM data for KV-Cache...<br>> Waking {selected_model}...", 60)
            time.sleep(1)
            
            update_log("> Neural synthesis initiated.<br>> Streaming report...", 90)
            
            report_container = st.container(border=True)
            report_text_box = report_container.empty()
            full_report = ""
            
            for chunk in generate_business_strategy_stream(st.session_state.location_name, infra_str, comp_str, rev_str, model_name=selected_model, api_keys=api_keys):
                chunk = chunk.replace("<thought>", "> **[Agent Thinking...]**\n> ").replace("</thought>", "\n\n")
                full_report += chunk
                report_text_box.markdown(full_report + "▌")
                
            report_text_box.markdown(full_report)
            update_log("> Analysis generated successfully.<br>> Process terminated.", 100)
            st.session_state.generated_report = full_report
        else:
            progress_bar.progress(100)
            log_box.empty()
        
        # Render Data Visualization (Always)
        st.markdown("#### Extracted Market Data")
        col_chart1, col_chart2 = st.columns(2)
        
        if st.session_state.get('infra_data'):
            fig1 = go.Figure(data=[go.Bar(x=list(st.session_state.infra_data.keys()), y=list(st.session_state.infra_data.values()), marker_color='#58A6FF')])
            fig1.update_layout(title="Local Infrastructure Density", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0, r=0, t=30, b=0))
            col_chart1.plotly_chart(fig1, use_container_width=True)
            
        if st.session_state.get('comp_count') is not None:
            fig2 = go.Figure(data=[go.Bar(x=['Competitors', 'Reviews'], y=[st.session_state.comp_count, st.session_state.rev_count], marker_color='#3FB950')])
            fig2.update_layout(title="Market Saturation (Scraped)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0, r=0, t=30, b=0))
            col_chart2.plotly_chart(fig2, use_container_width=True)
        
        if "generated_report" in st.session_state:
            with st.container(border=True):
                st.markdown(st.session_state.generated_report)
            
            col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
            with col_d1:
                st.download_button(
                    label="Download Markdown (.md)",
                    data=st.session_state.generated_report,
                    file_name=f"{st.session_state.location_name[:20].replace(' ', '_')}_Strategy.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with col_d2:
                components.html("""
                <button onclick="window.parent.print()" style="width:100%; background-color:#238636; color:white; padding:10px 20px; border:none; border-radius:5px; font-weight:bold; font-size:14px; cursor:pointer; font-family:sans-serif;">
                   Print / Save as PDF
                </button>
                """, height=50)
            with col_d3:
                if st.button("Reset Map", use_container_width=True):
                    st.session_state.view = 'map'
                    del st.session_state['generated_report']
                    st.rerun()
            
            st.markdown("---")
            st.markdown("### Discuss this Report with AI")
            
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # Suggested Follow-Up Questions
            st.markdown("**Suggested follow-ups:**")
            sq1, sq2, sq3 = st.columns(3)
            if sq1.button("Search current rent prices?", use_container_width=True):
                st.session_state.prompt_clicked = "Search online for the current commercial rent prices for this business in this area"
            if sq2.button("What is the biggest risk?", use_container_width=True):
                st.session_state.prompt_clicked = "Based on this report, what is the biggest risk for this business?"
            if sq3.button("Marketing strategies?", use_container_width=True):
                st.session_state.prompt_clicked = "What are 3 low-cost marketing strategies to acquire customers here?"

            prompt = st.chat_input("Ask a follow-up question...")
            if 'prompt_clicked' in st.session_state:
                prompt = st.session_state.prompt_clicked
                del st.session_state.prompt_clicked
                
            if prompt:
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    response_container = st.empty()
                    full_response = ""
                    for chunk in chat_with_report(st.session_state.generated_report, prompt, st.session_state.chat_history[:-1], model_name=selected_model, api_keys=api_keys):
                        full_response += chunk
                        response_container.markdown(full_response + "▌")
                    response_container.markdown(full_response)
                    
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                st.rerun()

    except Exception as e:
        update_log(f"> [ERROR] Execution Failed.<br>> Details: {e}", 100)
