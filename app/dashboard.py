import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Mumbai Locality Intelligence", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        border: 1px solid #333;
    }
    .metric-title {
        color: #888;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        color: #FFF;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }
    .cluster-badge {
        background-color: #667eea;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

def load_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    df = pd.read_csv(os.path.join(project_root, "data", "processed", "final_dataset.csv"))
    
    models_dir = os.path.join(project_root, "models")
    feature_cols = joblib.load(os.path.join(models_dir, "feature_cols.joblib"))
    
    BUSINESS_TYPES = ["restaurant", "cafe", "gym", "pharmacy", "beauty_salon", "store", "school", "lodging", "bar", "night_club"]
    
    models = {}
    for bt in BUSINESS_TYPES:
        models[bt] = joblib.load(os.path.join(models_dir, f"rf_{bt}.joblib"))
        
    return df, feature_cols, models

try:
    df, feature_cols, models = load_data()
except Exception as e:
    st.error("Failed to load data. Ensure the pipeline has finished successfully.")
    st.stop()

if "selected_loc" not in st.session_state:
    st.session_state.selected_loc = sorted(df['name'].unique())[0]

with st.sidebar:
    st.markdown("## Location Selection")
    localities = sorted(df['name'].unique())
    
    def update_loc():
        st.session_state.selected_loc = st.session_state.sidebar_dropdown
        
    st.selectbox(
        "Search Locality", 
        localities, 
        index=localities.index(st.session_state.selected_loc) if st.session_state.selected_loc in localities else 0,
        key="sidebar_dropdown",
        on_change=update_loc
    )
    selected_loc = st.session_state.selected_loc
    
    st.markdown("---")
    st.markdown("### Zone Filter")
    zone = df[df['name'] == selected_loc]['zone'].values[0]
    st.markdown(f"**Current Zone:** {zone}")

loc_data = df[df['name'] == selected_loc].iloc[0]

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"<h1 style='margin-bottom:0;'>{selected_loc}</h1>", unsafe_allow_html=True)
    st.markdown(f"<span class='cluster-badge'>{loc_data['cluster_label']}</span>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# Metrics Row
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Footfall Score</div>
        <div class="metric-value">{loc_data['overall_footfall']:.1f} / 100</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Avg Comm. Rent</div>
        <div class="metric-value">₹{loc_data['est_rent_sqft']:,.0f} /sqft</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Rent Tier</div>
        <div class="metric-value">{loc_data['rent_tier']}</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Offices</div>
        <div class="metric-value">{loc_data['offices']:.0f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_map, col_chart = st.columns([1, 1])

with col_map:
    st.markdown("### Location Overview")
    
    # Create a color and size column for the map
    df_map = df.copy()
    df_map['is_selected'] = df_map['name'] == selected_loc
    df_map['marker_color'] = df_map['is_selected'].map({False: '#555555', True: '#667eea'})
    df_map['marker_size'] = df_map['is_selected'].map({False: 8, True: 24})
    
    # Sort so the selected point is plotted last (on top)
    df_map = df_map.sort_values('is_selected')
    
    fig_map = go.Figure(go.Scattermapbox(
        lat=df_map['lat'],
        lon=df_map['lng'],
        mode='markers',
        marker=dict(
            size=df_map['marker_size'],
            color=df_map['marker_color'],
            opacity=1.0
        ),
        text=df_map['name'],
        hoverinfo='text'
    ))
    
    fig_map.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_center={"lat": loc_data['lat'], "lon": loc_data['lng']},
        mapbox_zoom=12,
        margin={"r":0,"t":0,"l":0,"b":0},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        showlegend=False
    )
    event = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
    
    points = getattr(event.selection, "points", [])
    if points:
        clicked_name = points[0].get("text", "") if isinstance(points[0], dict) else getattr(points[0], "text", "")
        if clicked_name and clicked_name != st.session_state.selected_loc:
            st.session_state.selected_loc = clicked_name
            st.rerun()

with col_chart:
    x_pred = pd.DataFrame([loc_data[feature_cols].fillna(0)])
    preds = []
    for bt, model in models.items():
        score = min(model.predict(x_pred)[0], 99.0)
        preds.append({"Business Type": bt.replace('_', ' ').title(), "Success Probability (%)": score})
    
    pred_df = pd.DataFrame(preds).sort_values("Success Probability (%)", ascending=True)
    
    st.markdown("### Business Recommendations")
    
    fig = px.bar(
        pred_df, 
        x="Success Probability (%)", 
        y="Business Type", 
        orientation='h',
        color="Success Probability (%)",
        color_continuous_scale="Viridis",
        text_auto='.1f'
    )
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(showgrid=True, gridcolor="#333", title="", range=[0, 100]),
        yaxis=dict(title="", showgrid=False),
        height=400,
        coloraxis_showscale=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown("### Footfall Breakdown")
    # Radar Chart for Time of Day
    categories = ['Morning (Commute)', 'Office Hours', 'Evening/Night', 'Weekend']
    values = [loc_data['morning_footfall'], loc_data['office_hr_footfall'], loc_data['evening_footfall'], loc_data['weekend_footfall']]
    
    fig_radar = go.Figure(data=go.Scatterpolar(
      r=values + [values[0]],
      theta=categories + [categories[0]],
      fill='toself',
      line_color='#667eea'
    ))
    fig_radar.update_layout(
      polar=dict(
        radialaxis=dict(visible=True, range=[0, 100], gridcolor="#333"),
        bgcolor="rgba(0,0,0,0)"
      ),
      plot_bgcolor="rgba(0,0,0,0)",
      paper_bgcolor="rgba(0,0,0,0)",
      font_color="#FFF",
      margin=dict(l=40, r=40, t=20, b=20),
      height=300
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    
    with st.expander("How is Footfall calculated?"):
        st.markdown("""
        **Footfall** is mathematically modeled from the density of nearby infrastructure (via OpenStreetMap):
        * **Morning:** Weighted by Railway Stations & Bus Stops.
        * **Office Hours:** Driven by Corporate Offices & Colleges.
        * **Evening:** Scaled by Malls, Restaurants & Bars.
        * **Weekend:** Dominated by Malls, Theatres & Tourist Spots.
        
        The scores are aggregated and normalized (0-100) relative to all Mumbai localities.
        """)

with c2:
    st.markdown("### Infrastructure Profile")
    inf_cols = ['malls', 'colleges', 'railway_stations', 'parking_lots']
    inf_vals = [loc_data[c] for c in inf_cols]
    
    fig_bar = px.bar(
        x=[c.replace('_', ' ').title() for c in inf_cols], 
        y=inf_vals,
        color_discrete_sequence=['#667eea']
    )
    fig_bar.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#FFF",
        margin=dict(l=0, r=0, t=20, b=20),
        xaxis=dict(title=""),
        yaxis=dict(title="Count", gridcolor="#333"),
        height=300
    )
    st.plotly_chart(fig_bar, use_container_width=True)
