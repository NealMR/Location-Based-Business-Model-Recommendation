"""
dashboard.py
------------
Locality — Mumbai market intelligence.

Design system: light "map-paper" surface, marine-navy ink, teal working hue,
marigold reserved exclusively for the selected locality ("you are here").
Every chart card carries a view toggle with a convention-correct alternative
(ranked bars <-> dots, paired bars <-> dumbbells, radar <-> bars, map/scatter <-> table).
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from common import BUSINESS_TYPES, model_path as canonical_model_path, compute_footfall_scores
from report import build_report

st.set_page_config(
    page_title="Locality — Mumbai market intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
INK = "#152238"        # marine navy — headings, values
INK2 = "#5B6779"       # secondary text
MUTED = "#8A94A6"      # captions, axis ticks
LINE = "#E4E8EF"       # hairlines, grid
PAPER = "#F6F8FB"      # app background
CARD = "#FFFFFF"

TEAL = "#0891B2"       # working data hue
MARIGOLD = "#B45309"   # reserved: the selected locality, everywhere
VIOLET = "#6D28D9"     # second series
MAGENTA = "#BE185D"    # third series
NEUTRAL = "#94A3B8"    # baseline / "before" series
GREEN = "#15803D"      # status: good
RED = "#B91C1C"        # status: serious

CLUSTER_COLORS = {     # identity — fixed order, never cycled
    "Corporate Hub": TEAL,
    "Commercial Market": VIOLET,
    "Student Zone": MAGENTA,
    "Residential Area": "#4D7C0F",
    "Mixed-Use Locality": NEUTRAL,
}
TAG_COLORS = {
    "Blue Ocean": TEAL,
    "Growing": VIOLET,
    "Saturated": RED,
    "Low Demand": NEUTRAL,
    "Unknown": LINE,
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --ink: #152238;
    --ink2: #5B6779;
    --muted: #8A94A6;
    --line: #E4E8EF;
    --paper: #F6F8FB;
    --card: #FFFFFF;
    --teal: #0891B2;
    --teal-deep: #0E7490;
    --marigold: #B45309;
    --radius: 14px;
}

html, body, [class*="css"] { font-family: 'Instrument Sans', sans-serif; }

.stApp { background-color: var(--paper); color: var(--ink); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
section[data-testid="stSidebar"] { display: none !important; }
.block-container {
    max-width: 1240px;
    padding-top: 2.2rem !important;
    padding-bottom: 3rem !important;
}

h1, h2, h3, .display {
    font-family: 'Bricolage Grotesque', sans-serif !important;
    color: var(--ink);
    letter-spacing: -0.02em;
}

/* ---- Brand row ---- */
.wordmark {
    font-family: 'Bricolage Grotesque', sans-serif !important;
    font-size: 1.9rem !important; font-weight: 700; color: var(--ink);
    letter-spacing: -0.03em; line-height: 1.1; margin: 0;
}
.wordmark .dot { color: var(--marigold); }
.brand-sub { color: var(--ink2); font-size: 0.92rem; margin: 0.15rem 0 0 0; }

/* ---- Context chips ---- */
.chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 1.1rem 0 0.4rem 0; }
.chip {
    background: var(--card); border: 1px solid var(--line); border-radius: 999px;
    padding: 6px 14px; font-size: 0.82rem; color: var(--ink2);
}
.chip b { color: var(--ink); font-weight: 600; margin-left: 4px; }
.chip.you { border-color: var(--marigold); color: var(--marigold); }
.chip.you b { color: var(--marigold); }

/* ---- Cards ---- */
.card-h {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 12px; margin: 0.4rem 0 0.1rem 0;
}
.eyebrow {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.09em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 0.15rem;
}
.card-title {
    font-family: 'Bricolage Grotesque', sans-serif;
    font-size: 1.12rem; font-weight: 600; color: var(--ink); margin: 0;
}
.card-note { color: var(--muted); font-size: 0.82rem; margin-top: 0.1rem; }

/* ---- Metric tiles ---- */
.metric-card {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
    padding: 1rem 1.15rem; margin-bottom: 0.75rem;
    transition: border-color 0.15s ease;
}
.metric-card:hover { border-color: var(--teal); }
.metric-title {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 0.3rem;
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace; font-size: 1.45rem;
    font-weight: 600; color: var(--ink); line-height: 1.15;
}
.metric-card.winner { border-color: var(--teal); box-shadow: 0 0 0 1px var(--teal) inset; }

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; border-bottom: 1px solid var(--line) !important;
    background: transparent !important; overflow-x: auto;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; border: none !important;
    padding: 10px 14px !important; color: var(--ink2) !important;
    font-size: 0.95rem !important; font-weight: 500 !important; white-space: nowrap;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--ink) !important; }
.stTabs [aria-selected="true"] {
    color: var(--teal-deep) !important; font-weight: 600 !important;
    border-bottom: 2px solid var(--teal-deep) !important; border-radius: 0 !important;
}
.stTabs [data-baseweb="tab-highlight-container"] { display: none !important; }

/* ---- Tables ---- */
.custom-table {
    width: 100%; border-collapse: collapse; margin: 0.6rem 0;
    font-size: 0.88rem; background: var(--card);
    border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden;
}
.custom-table th {
    border-bottom: 1px solid var(--line); color: var(--muted);
    font-weight: 600; padding: 10px 14px; font-size: 0.72rem;
    letter-spacing: 0.07em; text-transform: uppercase; background: var(--paper);
}
.custom-table td {
    border-bottom: 1px solid var(--line); color: var(--ink); padding: 10px 14px;
    font-variant-numeric: tabular-nums;
}
.custom-table tr:last-child td { border-bottom: none; }
.custom-table tr:hover td { background: var(--paper); }
.table-scroll { overflow-x: auto; }

/* ---- Segmented control (view toggle) ---- */
div[data-testid="stSegmentedControl"] button {
    font-size: 0.8rem !important; padding: 2px 12px !important;
}

/* ---- Expander / info ---- */
details { border-radius: var(--radius) !important; }

/* ---- Responsive ---- */
@media (max-width: 740px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; padding-top: 1.2rem !important; }
    .wordmark { font-size: 1.5rem; }
    .metric-value { font-size: 1.2rem; }
    .chip { font-size: 0.76rem; padding: 5px 10px; }
    .card-h { flex-direction: column; align-items: flex-start; gap: 4px; }
}

/* ---- "How this works" floating help ---- */
.help-fab {
    position: fixed; right: 22px; bottom: 22px; z-index: 9999;
    font-family: 'Instrument Sans', sans-serif;
}
.help-fab .fab-btn {
    width: 46px; height: 46px; border-radius: 50%;
    background: var(--ink); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.15rem; font-weight: 600; cursor: pointer;
    box-shadow: 0 4px 16px rgba(21,34,56,0.25);
    transition: transform 0.15s ease;
}
.help-fab:hover .fab-btn, .help-fab:focus-within .fab-btn { transform: scale(1.06); }
.help-fab .fab-panel {
    position: fixed; right: 20px; bottom: 80px; width: 330px; max-width: 86vw;
    background: var(--card); border: 1px solid var(--line); border-radius: 16px;
    box-shadow: 0 12px 40px rgba(21,34,56,0.16);
    padding: 18px 20px; opacity: 0; visibility: hidden; transform: translateY(6px);
    transition: opacity 0.18s ease, transform 0.18s ease, visibility 0.18s;
    max-height: 70vh; overflow-y: auto;
}
.help-fab:hover .fab-panel, .help-fab:focus-within .fab-panel {
    opacity: 1; visibility: visible; transform: translateY(0);
}
.fab-panel h4 {
    font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.02rem;
    color: var(--ink); margin: 0 0 10px 0;
}
.fab-panel h5 {
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.07em;
    text-transform: uppercase; color: var(--marigold); margin: 12px 0 3px 0;
}
.fab-panel p { font-size: 0.83rem; color: var(--ink2); margin: 0; line-height: 1.45; }

@media (max-width: 740px) {
    .help-fab { right: 12px; bottom: 12px; }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def card_header(eyebrow, title, note=None):
    note_html = f'<div class="card-note">{note}</div>' if note else ""
    st.markdown(
        f'<div class="eyebrow">{eyebrow}</div>'
        f'<div class="card-h"><h3 class="card-title">{title}</h3></div>{note_html}',
        unsafe_allow_html=True,
    )


def view_toggle(key, options):
    """The signature control: convention-correct alternate views for a chart."""
    return st.segmented_control(
        "View", options, key=key, default=options[0], label_visibility="collapsed"
    )


def style_fig(fig, height=380):
    fig.update_layout(
        template=None,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Instrument Sans, sans-serif", color=INK2, size=12),
        height=height, margin=dict(l=0, r=10, t=10, b=0),
        xaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE,
                   tickfont=dict(color=MUTED, size=11), automargin=True),
        yaxis=dict(gridcolor=LINE, zerolinecolor=LINE, linecolor=LINE,
                   tickfont=dict(color=INK2, size=11), automargin=True),
        hoverlabel=dict(bgcolor=CARD, bordercolor=LINE,
                        font=dict(color=INK, size=12, family="Instrument Sans, sans-serif")),
        legend=dict(orientation="h", y=1.1, x=0, font=dict(color=INK2)),
    )
    return fig


PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


def plot(fig, **kwargs):
    st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG, **kwargs)


def ranked_chart(labels, values, kind, height=380, x_title="", color=TEAL, hovertext=None):
    """Ranked categorical magnitude: horizontal bars <-> dot plot."""
    order = np.argsort(values)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    hovertext = [hovertext[i] for i in order] if hovertext else None

    fig = go.Figure()
    if kind == "Bars":
        fig.add_trace(go.Bar(
            x=values, y=labels, orientation="h",
            marker=dict(color=color, cornerradius=4),
            width=0.55, text=[f"{v:.0f}" for v in values],
            textposition="outside", textfont=dict(color=INK2, size=11),
            hovertext=hovertext, hoverinfo="text" if hovertext else None,
        ))
    else:  # Dots
        for lab, val in zip(labels, values):
            fig.add_shape(type="line", x0=0, x1=val, y0=lab, y1=lab,
                          line=dict(color=LINE, width=2), layer="below")
        fig.add_trace(go.Scatter(
            x=values, y=labels, mode="markers+text",
            marker=dict(size=11, color=color),
            text=[f"{v:.0f}" for v in values], textposition="middle right",
            textfont=dict(color=INK2, size=11),
            hovertext=hovertext, hoverinfo="text" if hovertext else None,
        ))
    style_fig(fig, height)
    fig.update_layout(xaxis_title=x_title,
                      yaxis=dict(title="", showgrid=False, automargin=True),
                      showlegend=False)
    return fig


def paired_chart(cats, a_vals, b_vals, a_name, b_name, a_color, b_color,
                 kind, height=430, x_title=""):
    """Paired comparison per category: grouped bars <-> dumbbell."""
    fig = go.Figure()
    if kind == "Bars":
        fig.add_trace(go.Bar(y=cats, x=a_vals, name=a_name, orientation="h",
                             marker=dict(color=a_color, cornerradius=3), width=0.34))
        fig.add_trace(go.Bar(y=cats, x=b_vals, name=b_name, orientation="h",
                             marker=dict(color=b_color, cornerradius=3), width=0.34))
        fig.update_layout(barmode="group")
    else:  # Dumbbell
        xs, ys = [], []
        for c, a, b in zip(cats, a_vals, b_vals):
            xs += [a, b, None]
            ys += [c, c, None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                                 line=dict(color=LINE, width=2.5),
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=a_vals, y=cats, mode="markers", name=a_name,
                                 marker=dict(size=11, color=a_color)))
        fig.add_trace(go.Scatter(x=b_vals, y=cats, mode="markers", name=b_name,
                                 marker=dict(size=11, color=b_color)))
    style_fig(fig, height)
    fig.update_layout(xaxis_title=x_title,
                      yaxis=dict(title="", showgrid=False, automargin=True))
    return fig


def render_custom_table(dataframe, formats=None, align=None, column_styles=None):
    formats = formats or {}
    align = align or {}
    column_styles = column_styles or {}

    html = '<div class="table-scroll"><table class="custom-table"><thead><tr>'
    for col in dataframe.columns:
        html += f'<th style="text-align:{align.get(col, "left")}">{col}</th>'
    html += '</tr></thead><tbody>'
    for _, row in dataframe.iterrows():
        html += '<tr>'
        for col in dataframe.columns:
            val = row[col]
            if col in formats:
                val_str = formats[col](val) if callable(formats[col]) else formats[col].format(val)
            else:
                val_str = str(val)
            style = f'text-align:{align.get(col, "left")}'
            if col in column_styles:
                style += f'; {column_styles[col](val) if callable(column_styles[col]) else column_styles[col]}'
            html += f'<td style="{style}">{val_str}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    return html


INFRA_COLS = [
    'railway_stations', 'metro_stations', 'bus_stops', 'colleges', 'schools',
    'offices', 'malls', 'hospitals', 'parking_lots', 'tourist_spots',
    'existing_cafes', 'existing_restaurants', 'existing_gyms'
]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    models_dir = os.path.join(project_root, "models")

    enriched_path = os.path.join(project_root, "data", "processed", "enriched_dataset.csv")
    final_path = os.path.join(project_root, "data", "processed", "final_dataset.csv")
    data_path = enriched_path if os.path.exists(enriched_path) else final_path

    df = pd.read_csv(data_path)
    feature_cols = joblib.load(os.path.join(models_dir, "feature_cols.joblib"))

    models = {}
    for bt in BUSINESS_TYPES:
        path = canonical_model_path(bt)
        if os.path.exists(path):
            # Safe: models are trained and written locally by scripts/08_model.py
            models[bt] = joblib.load(path)

    shap_path = os.path.join(models_dir, "shap_importance.json")
    shap_importance = {}
    if os.path.exists(shap_path):
        with open(shap_path, 'r') as f:
            shap_importance = json.load(f)

    metrics_path = os.path.join(models_dir, "metrics_report.csv")
    metrics_df = pd.read_csv(metrics_path) if os.path.exists(metrics_path) else pd.DataFrame()

    conf_path = os.path.join(models_dir, "model_confidence.json")
    confidence = {}
    if os.path.exists(conf_path):
        with open(conf_path, 'r') as f:
            confidence = json.load(f)

    neighbors, gap_report = {}, {}
    nb_path = os.path.join(models_dir, "neighbors.json")
    if os.path.exists(nb_path):
        with open(nb_path, 'r') as f:
            neighbors = json.load(f)
    gr_path = os.path.join(models_dir, "gap_report.json")
    if os.path.exists(gr_path):
        with open(gr_path, 'r') as f:
            gap_report = json.load(f)

    return df, feature_cols, models, shap_importance, metrics_df, confidence, neighbors, gap_report


try:
    df, feature_cols, models, shap_importance, metrics_df, confidence, neighbors, gap_report = load_data()
except Exception as e:
    st.error(f"Couldn't load the dataset: {e}")
    st.info("Run the pipeline first: `python scripts/run_all.py`")
    st.stop()

localities = sorted(df['name'].unique())

if "selected_loc" not in st.session_state:
    st.session_state.selected_loc = localities[0]


def update_loc():
    st.session_state.selected_loc = st.session_state.top_dropdown


# ---------------------------------------------------------------------------
# Brand row + context
# ---------------------------------------------------------------------------
col_brand, col_selector = st.columns([2.2, 1])
with col_brand:
    st.markdown(
        '<p class="wordmark">Locality<span class="dot">.</span></p>'
        '<p class="brand-sub">Where should a business open in Mumbai — and why.</p>',
        unsafe_allow_html=True,
    )
with col_selector:
    st.selectbox(
        "Choose a locality", localities,
        index=localities.index(st.session_state.selected_loc) if st.session_state.selected_loc in localities else 0,
        key="top_dropdown", on_change=update_loc,
    )

selected_loc = st.session_state.selected_loc
loc_data = df[df['name'] == selected_loc].iloc[0]
zone = loc_data['zone']
cluster = loc_data.get('cluster_label', 'Unknown')
footfall_val = loc_data.get('overall_footfall', 0)
rent_val = loc_data.get('est_rent_sqft', 0)

st.markdown(f"""
<div class="chip-row">
    <span class="chip you">📍<b>{selected_loc}</b></span>
    <span class="chip">Zone<b>{zone}</b></span>
    <span class="chip">Profile<b>{cluster}</b></span>
    <span class="chip">Foot traffic<b>{footfall_val:.0f} / 100</b></span>
    <span class="chip">Rent<b>₹{rent_val:,.0f} / sq ft</b></span>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Explore", "Why these scores", "Market view", "Compare", "Simulate", "Peer gaps", "Report"
])

# Floating "How this site works" help — visible on every tab
st.markdown("""
<div class="help-fab" tabindex="0" aria-label="How this site works">
    <div class="fab-btn">?</div>
    <div class="fab-panel">
        <h4>How this site works</h4>
        <h5>How predictions are made</h5>
        <p>We count what's physically around each of 137 Mumbai localities — stations,
        offices, schools, malls — using OpenStreetMap, add government rent rates, and
        train a model to estimate how well each business type tends to do in places
        that look like this one.</p>
        <h5>The data</h5>
        <p>Everything comes from public sources: OpenStreetMap for infrastructure and
        business counts, Maharashtra Ready Reckoner rates for rent. No private or
        personal data is used.</p>
        <h5>How reliable is it</h5>
        <p>We test every model by hiding entire zones of the city and asking it to
        predict them. Typical error is about ±20 points on a 0–100 scale — good for
        direction, not certainty. Each chart tells you its own error.</p>
        <h5>The honest truth</h5>
        <p>No tool can promise a business will succeed. Scores are screening signals.
        Where our numbers are weak, we say so right on the chart instead of hiding it.</p>
        <h5>User-first policy</h5>
        <p>Plain language over jargon, caveats next to every claim, and nothing dressed
        up to look more precise than it is. The report you can download says the same
        things this site does — including the doubts.</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ===========================================================================
# TAB 1 — EXPLORE
# ===========================================================================
with tab1:
    m1, m2, m3, m4 = st.columns(4)
    for col, title, value in [
        (m1, "Foot traffic", f"{footfall_val:.0f} / 100"),
        (m2, "Commercial rent", f"₹{rent_val:,.0f} /sq ft"),
        (m3, "Rent tier", f"{str(loc_data.get('rent_tier', '—')).title()}"),
        (m4, "Offices nearby", f"{loc_data.get('offices', 0):.0f}"),
    ]:
        col.markdown(
            f'<div class="metric-card"><div class="metric-title">{title}</div>'
            f'<div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    col_map, col_chart = st.columns([1, 1])

    # ---- Map / table ----
    with col_map:
        card_header("City overview", "All localities",
                    "Marigold marks your selected locality. Click any point to switch.")
        map_view = view_toggle("view_map", ["Map", "Table"])

        if map_view == "Map":
            df_map = df.copy()
            df_map['is_selected'] = df_map['name'] == selected_loc
            df_sel = df_map[df_map['is_selected']]
            df_rest = df_map[~df_map['is_selected']]

            fig_map = go.Figure()
            fig_map.add_trace(go.Densitymap(
                lat=df['lat'], lon=df['lng'], z=df['overall_footfall'], radius=18,
                colorscale=[[0, 'rgba(0,0,0,0)'], [0.5, 'rgba(8,145,178,0.08)'],
                            [1, 'rgba(8,145,178,0.22)']],
                showscale=False, hoverinfo='skip',
            ))
            fig_map.add_trace(go.Scattermap(
                lat=df_rest['lat'], lon=df_rest['lng'], mode='markers',
                marker=dict(size=10, color=[CLUSTER_COLORS.get(c, NEUTRAL)
                                            for c in df_rest.get('cluster_label', 'Unknown')],
                            opacity=0.75),
                text=df_rest.apply(lambda r: (
                    f"<b>{r['name']}</b><br>{r.get('cluster_label', '—')}<br>"
                    f"Foot traffic {r.get('overall_footfall', 0):.0f} · "
                    f"₹{r.get('est_rent_sqft', 0):,.0f}/sq ft"), axis=1),
                customdata=df_rest['name'], hoverinfo='text', name="",
            ))
            fig_map.add_trace(go.Scattermap(
                lat=df_sel['lat'], lon=df_sel['lng'], mode='markers',
                marker=dict(size=20, color=MARIGOLD, opacity=1.0),
                text=df_sel.apply(lambda r: (
                    f"<b>{r['name']}</b> — selected<br>{r.get('cluster_label', '—')}"), axis=1),
                customdata=df_sel['name'], hoverinfo='text', name="",
            ))
            fig_map.update_layout(
                map=dict(style="carto-positron",
                         center={"lat": float(loc_data['lat']), "lon": float(loc_data['lng'])},
                         zoom=11.6),
                margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=430, showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            event = st.plotly_chart(fig_map, use_container_width=True,
                                    on_select="rerun", config=PLOT_CONFIG)
            points = getattr(event.selection, "points", [])
            if points:
                pt = points[0] if isinstance(points[0], dict) else points[0].__dict__
                clicked_name = pt.get("customdata")
                if isinstance(clicked_name, (list, tuple)):
                    clicked_name = clicked_name[0]
                if clicked_name and clicked_name in localities and clicked_name != st.session_state.selected_loc:
                    st.session_state.selected_loc = clicked_name
                    st.rerun()
        else:
            tbl = df[['name', 'zone', 'cluster_label', 'overall_footfall', 'est_rent_sqft']].copy()
            tbl.columns = ['Locality', 'Zone', 'Profile', 'Foot traffic', 'Rent / sq ft']
            tbl = tbl.sort_values('Foot traffic', ascending=False).head(25)
            st.markdown(render_custom_table(
                tbl,
                formats={'Foot traffic': '{:.0f}', 'Rent / sq ft': '₹{:,.0f}'},
                align={'Foot traffic': 'right', 'Rent / sq ft': 'right'},
            ), unsafe_allow_html=True)
            st.caption("Top 25 by foot traffic. Use the selector above to jump to any locality.")

    # ---- Recommendations ----
    with col_chart:
        card_header("Model estimate", f"What could work in {selected_loc}",
                    "Viability, 0–100. Hover for the score band and typical error.")
        rec_view = view_toggle("view_rec", ["Bars", "Dots"])

        x_pred = pd.DataFrame([loc_data[feature_cols].fillna(0)])
        labels, values, hovers = [], [], []
        for bt, model in models.items():
            score = float(np.clip(model.predict(x_pred)[0], 0, 99))
            conf = confidence.get(bt, {})
            mae = conf.get('cv_mae')
            band = "Strong" if score >= 60 else ("Moderate" if score >= 35 else "Weak")
            tag = loc_data.get(f"{bt}_market_tag", "")
            labels.append(bt.replace('_', ' ').title())
            values.append(score)
            hovers.append(f"<b>{bt.replace('_', ' ').title()}</b><br>{band} · {tag}"
                          + (f"<br>Typical error ±{mae:.0f} pts" if mae else ""))

        plot(ranked_chart(labels, values, rec_view, height=430,
                          x_title="Viability score", hovertext=hovers))

        if confidence:
            avg_mae = np.mean([c.get('cv_mae', 0) for c in confidence.values()])
            st.caption(
                f"Scores carry a typical error of ±{avg_mae:.0f} points (spatial cross-validation). "
                f"Read them as direction, not probability."
            )

    # ---- Plain-English why ----
    with st.expander("Why these scores, in plain English"):
        pred_df = pd.DataFrame({"Business": labels, "Score": values})
        top3 = pred_df.sort_values("Score", ascending=False).head(3)
        for _, p in top3.iterrows():
            bt_key = p["Business"].lower().replace(' ', '_')
            drivers = shap_importance.get(bt_key, {}).get('mean_abs_shap', {})
            reasons = []
            for feat in list(drivers.keys())[:3]:
                if feat not in df.columns:
                    continue
                val = float(loc_data.get(feat, 0) or 0)
                avg = float(df[feat].mean())
                direction = "above" if val > avg else "below"
                reasons.append(f"**{feat.replace('_', ' ')}** is {direction} the city average ({val:.0f} vs {avg:.0f})")
            reason_text = "; ".join(reasons) if reasons else "driver data not available"
            band = "Strong" if p['Score'] >= 60 else ("Moderate" if p['Score'] >= 35 else "Weak")
            st.markdown(f"- **{p['Business']}** scores **{p['Score']:.0f} ({band})**. "
                        f"The model reacted mostly to: {reason_text}.")
        st.caption("These describe what the model responded to — not a guarantee of business success.")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)

    # ---- Footfall profile ----
    with c1:
        card_header("Rhythm of the day", "When people are here",
                    "Estimated foot traffic by time of day, 0–100.")
        ff_view = view_toggle("view_ff", ["Radar", "Bars"])
        ff_cats = ['Morning', 'Office hours', 'Evening', 'Weekend']
        ff_vals = [loc_data.get(k, 0) for k in
                   ['morning_footfall', 'office_hr_footfall', 'evening_footfall', 'weekend_footfall']]

        if ff_view == "Radar":
            fig_ff = go.Figure(go.Scatterpolar(
                r=ff_vals + [ff_vals[0]], theta=ff_cats + [ff_cats[0]],
                fill='toself', line=dict(color=TEAL, width=2),
                fillcolor='rgba(8,145,178,0.10)', marker=dict(size=6, color=TEAL),
            ))
            style_fig(fig_ff, 330)
            fig_ff.update_layout(polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor=LINE,
                                tickfont=dict(color=MUTED, size=10)),
                angularaxis=dict(gridcolor=LINE, tickfont=dict(color=INK2, size=11)),
                bgcolor="rgba(0,0,0,0)"),
                margin=dict(l=50, r=50, t=30, b=30), showlegend=False)
            plot(fig_ff)
        else:
            fig_ff = go.Figure(go.Bar(
                x=ff_cats, y=ff_vals, marker=dict(color=TEAL, cornerradius=4), width=0.5,
                text=[f"{v:.0f}" for v in ff_vals], textposition="outside",
                textfont=dict(color=INK2, size=11),
            ))
            style_fig(fig_ff, 330)
            fig_ff.update_layout(yaxis=dict(range=[0, 110], title="Foot traffic"),
                                 xaxis=dict(showgrid=False), showlegend=False)
            plot(fig_ff)

    # ---- Infrastructure ----
    with c2:
        card_header("What's on the ground", "Infrastructure within reach",
                    "Counts from OpenStreetMap around this locality.")
        inf_view = view_toggle("view_inf", ["Bars", "Dots"])
        available_infra = [c for c in INFRA_COLS if c in df.columns]
        inf_labels = [c.replace('_', ' ').title() for c in available_infra]
        inf_vals = [float(loc_data.get(c, 0) or 0) for c in available_infra]
        plot(ranked_chart(inf_labels, inf_vals, inf_view, height=330, x_title="Count"))


# ===========================================================================
# TAB 2 — WHY THESE SCORES (feature attribution)
# ===========================================================================
with tab2:
    card_header("Model attribution", "What drives each prediction",
                "Global feature influence for the selected business type, plus how "
                f"{selected_loc} compares with the city average on those drivers.")

    if not shap_importance:
        st.info("Attribution data isn't available yet. Install `shap` and re-run `scripts/08_model.py`.")
    else:
        bt_select = st.selectbox(
            "Business type",
            [bt.replace('_', ' ').title() for bt in BUSINESS_TYPES],
            key="shap_bt",
        )
        bt_key = bt_select.lower().replace(' ', '_')

        if bt_key in shap_importance:
            shap_data = shap_importance[bt_key]
            feats = list(shap_data['mean_abs_shap'].keys())
            vals = list(shap_data['mean_abs_shap'].values())

            col_s1, col_s2 = st.columns([1.5, 1])
            with col_s1:
                card_header("Influence", f"Top drivers — {bt_select}")
                shap_view = view_toggle("view_shap", ["Bars", "Dots"])
                nice = [f.replace('_', ' ').title() for f in feats]
                plot(ranked_chart(nice, vals, shap_view, height=430,
                                  x_title="Attribution strength (mean |SHAP|)"))

            with col_s2:
                card_header("Local profile", f"{selected_loc} vs city average")
                sorted_feats = [f for _, f in sorted(zip(vals, feats), reverse=True)]
                rows = []
                for feat in sorted_feats[:8]:
                    val = float(loc_data.get(feat, 0) or 0)
                    avg = float(df[feat].mean()) if feat in df.columns else 0
                    rows.append({
                        "Driver": feat.replace('_', ' ').title(),
                        "Here": val, "City avg": avg, "Δ": val - avg,
                    })
                st.markdown(render_custom_table(
                    pd.DataFrame(rows),
                    formats={"Here": '{:.0f}', "City avg": '{:.0f}', "Δ": '{:+.0f}'},
                    align={"Here": 'right', "City avg": 'right', "Δ": 'right'},
                    column_styles={"Δ": lambda v: f'color:{GREEN if v > 0 else (RED if v < 0 else INK2)}; font-weight:600'},
                ), unsafe_allow_html=True)
        else:
            st.warning(f"No attribution data for {bt_select} — its best model is linear "
                       f"(see coefficients in models/model_confidence.json).")


# ===========================================================================
# TAB 3 — MARKET VIEW
# ===========================================================================
with tab3:
    card_header("Market intelligence", "Saturation, opportunity, and rough economics",
                "Pick a business sector to see which localities are crowded and which are open.")

    has_saturation = any(f"{bt}_saturation" in df.columns for bt in BUSINESS_TYPES)
    has_revenue = any(f"{bt}_est_roi_pct" in df.columns for bt in BUSINESS_TYPES)

    if not has_saturation:
        st.info("Run `scripts/09_enrich.py` to generate saturation and revenue data.")
    else:
        bt_market = st.selectbox(
            "Business sector",
            [bt.replace('_', ' ').title() for bt in BUSINESS_TYPES],
            key="market_bt",
        )
        bt_mk = bt_market.lower().replace(' ', '_')
        sat_col = f"{bt_mk}_saturation"
        via_col = f"{bt_mk}_viability_norm"
        tag_col = f"{bt_mk}_market_tag"

        col_m1, col_m2 = st.columns([1.35, 1])

        with col_m1:
            card_header("Positioning", "Traffic vs competition",
                        "Each point is a locality. Upper area = crowded; lower right = busy and open.")
            mkt_view = view_toggle("view_mkt", ["Scatter", "Table"])

            plot_df = df[['name', sat_col, via_col, 'overall_footfall']].copy()
            plot_df['tag'] = df[tag_col] if tag_col in df.columns else 'Unknown'
            plot_df['is_selected'] = plot_df['name'] == selected_loc

            if mkt_view == "Scatter":
                fig_gap = go.Figure()
                for tag_name, tag_color in TAG_COLORS.items():
                    sub = plot_df[(plot_df['tag'] == tag_name) & (~plot_df['is_selected'])]
                    if sub.empty:
                        continue
                    fig_gap.add_trace(go.Scatter(
                        x=sub['overall_footfall'], y=sub[sat_col], mode='markers',
                        name=tag_name,
                        marker=dict(size=9, color=tag_color, opacity=0.8,
                                    line=dict(width=1, color=CARD)),
                        text=sub['name'], hoverinfo='text+name',
                    ))
                sel_row = plot_df[plot_df['is_selected']]
                if not sel_row.empty:
                    fig_gap.add_trace(go.Scatter(
                        x=sel_row['overall_footfall'], y=sel_row[sat_col],
                        mode='markers+text', text=[selected_loc], textposition='top center',
                        textfont=dict(color=MARIGOLD, size=12, family="Instrument Sans"),
                        marker=dict(size=15, color=MARIGOLD, line=dict(width=2, color=CARD)),
                        showlegend=False, hoverinfo='skip',
                    ))
                fig_gap.add_vline(x=plot_df['overall_footfall'].mean(), line_width=1,
                                  line_dash="dash", line_color=LINE)
                fig_gap.add_hline(y=plot_df[sat_col].mean(), line_width=1,
                                  line_dash="dash", line_color=LINE)
                style_fig(fig_gap, 440)
                fig_gap.update_layout(xaxis_title="Foot traffic score",
                                      yaxis_title="Saturation index")
                plot(fig_gap)
            else:
                tbl = plot_df.sort_values(sat_col, ascending=False).head(20)[
                    ['name', 'tag', 'overall_footfall', sat_col]].copy()
                tbl.columns = ['Locality', 'Status', 'Foot traffic', 'Saturation']
                st.markdown(render_custom_table(
                    tbl, formats={'Foot traffic': '{:.0f}', 'Saturation': '{:.2f}'},
                    align={'Foot traffic': 'right', 'Saturation': 'right'},
                ), unsafe_allow_html=True)
                st.caption("Top 20 most saturated localities for this sector.")

        with col_m2:
            if has_revenue:
                card_header("Rough economics", f"{selected_loc} · {bt_market}")
                st.caption(
                    "Scenario estimates, not forecasts: industry-average revenue scaled by "
                    "viability and traffic; cost covers rent only. Compare localities with "
                    "them — don't plan a budget."
                )
                roi_col = f"{bt_mk}_est_roi_pct"
                rev_col = f"{bt_mk}_est_revenue_lakhs"
                cost_col = f"{bt_mk}_est_rent_cost_lakhs"

                if roi_col in df.columns:
                    loc_rev = loc_data.get(rev_col, 0)
                    loc_cost = loc_data.get(cost_col, 0)
                    loc_roi = loc_data.get(roi_col, 0)

                    fin1, fin2, fin3 = st.columns(3)
                    fin1.markdown(f'<div class="metric-card"><div class="metric-title">Revenue / mo</div>'
                                  f'<div class="metric-value">₹{loc_rev:.1f}L</div></div>',
                                  unsafe_allow_html=True)
                    fin2.markdown(f'<div class="metric-card"><div class="metric-title">Rent / mo</div>'
                                  f'<div class="metric-value">₹{loc_cost:.1f}L</div></div>',
                                  unsafe_allow_html=True)
                    roi_color = GREEN if loc_roi > 0 else RED
                    fin3.markdown(f'<div class="metric-card"><div class="metric-title">ROI</div>'
                                  f'<div class="metric-value" style="color:{roi_color}">{loc_roi:.0f}%</div></div>',
                                  unsafe_allow_html=True)

                    top_roi = df.nlargest(10, roi_col)[['name', rev_col, cost_col, roi_col]].copy()
                    top_roi.columns = ['Locality', 'Revenue', 'Rent', 'ROI']
                    st.markdown(render_custom_table(
                        top_roi,
                        formats={'Revenue': '₹{:.1f}L', 'Rent': '₹{:.1f}L', 'ROI': '{:.0f}%'},
                        align={'Revenue': 'right', 'Rent': 'right', 'ROI': 'right'},
                    ), unsafe_allow_html=True)

        # Blue Ocean table
        st.markdown("<br>", unsafe_allow_html=True)
        card_header("Open water", f"Underserved localities for {bt_market.lower()}",
                    "High predicted viability with few existing competitors.")
        if tag_col in df.columns:
            blue = df[df[tag_col] == 'Blue Ocean'][['name', 'zone', via_col, sat_col,
                                                    'overall_footfall', 'est_rent_sqft']].copy()
            blue.columns = ['Locality', 'Zone', 'Viability', 'Saturation', 'Foot traffic', 'Rent / sq ft']
            blue = blue.sort_values('Viability', ascending=False)
            if len(blue) > 0:
                st.markdown(render_custom_table(
                    blue,
                    formats={'Viability': '{:.0f}', 'Saturation': '{:.2f}',
                             'Foot traffic': '{:.0f}', 'Rent / sq ft': '₹{:,.0f}'},
                    align={'Viability': 'right', 'Saturation': 'right',
                           'Foot traffic': 'right', 'Rent / sq ft': 'right'},
                ), unsafe_allow_html=True)
            else:
                st.info(f"No underserved localities identified for {bt_market.lower()} right now.")


# ===========================================================================
# TAB 4 — COMPARE
# ===========================================================================
with tab4:
    card_header("Head to head", "Compare two localities",
                "Structural benchmarks, model estimates, and daily rhythm, side by side.")

    col_a, col_b = st.columns(2)
    with col_a:
        loc_a = st.selectbox("Locality A", localities, index=0, key="cmp_a")
    with col_b:
        loc_b = st.selectbox("Locality B", localities, index=min(1, len(localities) - 1), key="cmp_b")

    if loc_a and loc_b:
        data_a = df[df['name'] == loc_a].iloc[0]
        data_b = df[df['name'] == loc_b].iloc[0]

        metrics = [
            ("Foot traffic", 'overall_footfall', '{:.0f}'),
            ("Rent / sq ft", 'est_rent_sqft', '₹{:,.0f}'),
            ("Offices", 'offices', '{:.0f}'),
            ("Malls", 'malls', '{:.0f}'),
            ("Colleges", 'colleges', '{:.0f}'),
        ]
        cmp_cols = st.columns(len(metrics))
        for col, (label, key, fmt) in zip(cmp_cols, metrics):
            va, vb = data_a.get(key, 0), data_b.get(key, 0)
            # Lower rent wins; higher wins everywhere else
            win_a = "winner" if (key != 'est_rent_sqft' and va > vb) or (key == 'est_rent_sqft' and va < vb) else ""
            win_b = "winner" if (key != 'est_rent_sqft' and vb > va) or (key == 'est_rent_sqft' and vb < va) else ""
            col.markdown(f"""
            <div class="metric-title" style="text-align:center; margin-bottom:6px;">{label}</div>
            <div class="metric-card {win_a}" style="text-align:center; padding:0.7rem;">
                <div class="metric-title" style="color:{TEAL}">{loc_a[:14]}</div>
                <div class="metric-value" style="font-size:1.15rem">{fmt.format(va)}</div>
            </div>
            <div class="metric-card {win_b}" style="text-align:center; padding:0.7rem;">
                <div class="metric-title" style="color:{VIOLET}">{loc_b[:14]}</div>
                <div class="metric-value" style="font-size:1.15rem">{fmt.format(vb)}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns([1.25, 1])

        with col_c1:
            card_header("Model estimates", "Viability, business by business")
            cmp_view = view_toggle("view_cmp", ["Bars", "Dumbbell"])
            cats, a_vals, b_vals = [], [], []
            for bt in BUSINESS_TYPES:
                if bt not in models:
                    continue
                x_a = pd.DataFrame([data_a[feature_cols].fillna(0)])
                x_b = pd.DataFrame([data_b[feature_cols].fillna(0)])
                cats.append(bt.replace('_', ' ').title())
                a_vals.append(float(np.clip(models[bt].predict(x_a)[0], 0, 99)))
                b_vals.append(float(np.clip(models[bt].predict(x_b)[0], 0, 99)))
            plot(paired_chart(cats, a_vals, b_vals, loc_a, loc_b, TEAL, VIOLET,
                              cmp_view, height=450, x_title="Viability score"))

        with col_c2:
            card_header("Daily rhythm", "Foot traffic through the day")
            rhythm_view = view_toggle("view_rhythm", ["Radar", "Bars"])
            ff_cats = ['Morning', 'Office hours', 'Evening', 'Weekend']
            ff_keys = ['morning_footfall', 'office_hr_footfall', 'evening_footfall', 'weekend_footfall']
            a_ff = [data_a.get(k, 0) for k in ff_keys]
            b_ff = [data_b.get(k, 0) for k in ff_keys]

            if rhythm_view == "Radar":
                fig_ff = go.Figure()
                for name, vals, color, rgba in [(loc_a, a_ff, TEAL, "8,145,178"),
                                                (loc_b, b_ff, VIOLET, "109,40,217")]:
                    fig_ff.add_trace(go.Scatterpolar(
                        r=vals + [vals[0]], theta=ff_cats + [ff_cats[0]],
                        fill='toself', name=name,
                        line=dict(color=color, width=2), fillcolor=f"rgba({rgba},0.08)",
                        marker=dict(size=5),
                    ))
                style_fig(fig_ff, 450)
                fig_ff.update_layout(polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor=LINE,
                                    tickfont=dict(color=MUTED, size=10)),
                    angularaxis=dict(gridcolor=LINE, tickfont=dict(color=INK2, size=11)),
                    bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=50, r=50, t=40, b=30))
                plot(fig_ff)
            else:
                fig_ff = go.Figure()
                fig_ff.add_trace(go.Bar(x=ff_cats, y=a_ff, name=loc_a,
                                        marker=dict(color=TEAL, cornerradius=3), width=0.3))
                fig_ff.add_trace(go.Bar(x=ff_cats, y=b_ff, name=loc_b,
                                        marker=dict(color=VIOLET, cornerradius=3), width=0.3))
                style_fig(fig_ff, 450)
                fig_ff.update_layout(barmode="group", yaxis=dict(range=[0, 110], title="Foot traffic"),
                                     xaxis=dict(showgrid=False))
                plot(fig_ff)


# ===========================================================================
# TAB 5 — SIMULATE
# ===========================================================================
with tab5:
    card_header("What-if", f"Reshape {selected_loc} and watch the estimates move",
                "Adjust local assets below. Derived foot-traffic scores update with your changes.")

    sim_features = {}
    cat1, cat2, cat3 = st.columns(3)
    slider_groups = [
        (cat1, "Transport", ['railway_stations', 'metro_stations', 'bus_stops', 'parking_lots']),
        (cat2, "Commercial", ['offices', 'malls', 'est_rent_sqft']),
        (cat3, "Social", ['colleges', 'schools', 'hospitals', 'tourist_spots']),
    ]
    for col, group_label, feats in slider_groups:
        with col:
            st.markdown(f'<div class="eyebrow" style="margin-top:0.6rem">{group_label}</div>',
                        unsafe_allow_html=True)
            for feat in feats:
                if feat not in feature_cols:
                    continue
                current = float(loc_data.get(feat, 0))
                if feat == 'est_rent_sqft':
                    sim_features[feat] = st.slider("Rent (₹/sq ft)", 0.0, 500.0, current,
                                                   step=10.0, key=f"sim_{feat}")
                else:
                    max_val = max(float(df[feat].max()) * 2, current * 2, 8.0)
                    sim_features[feat] = st.slider(feat.replace('_', ' ').title(), 0.0, max_val,
                                                   current, step=1.0, key=f"sim_{feat}")

    sim_row = loc_data[feature_cols].fillna(0).copy()
    for feat, val in sim_features.items():
        if feat in sim_row.index:
            sim_row[feat] = val

    # Recompute derived footfall from simulated raw features — otherwise the
    # model keeps seeing the OLD footfall and sliders barely move it
    for score_name, score_val in compute_footfall_scores(sim_row, df).items():
        if score_name in sim_row.index:
            sim_row[score_name] = score_val

    x_sim = pd.DataFrame([sim_row])
    x_orig = pd.DataFrame([loc_data[feature_cols].fillna(0)])
    cats, cur_vals, sim_vals = [], [], []
    for bt, model in models.items():
        cats.append(bt.replace('_', ' ').title())
        cur_vals.append(float(np.clip(model.predict(x_orig)[0], 0, 99)))
        sim_vals.append(float(np.clip(model.predict(x_sim)[0], 0, 99)))

    st.markdown("<br>", unsafe_allow_html=True)
    col_sim_chart, col_sim_table = st.columns([1.3, 1])

    with col_sim_chart:
        card_header("Impact", "Current vs simulated")
        sim_view = view_toggle("view_sim", ["Dumbbell", "Bars"])
        plot(paired_chart(cats, cur_vals, sim_vals, "Current", "Simulated",
                          NEUTRAL, TEAL, "Bars" if sim_view == "Bars" else "Dumbbell",
                          height=450, x_title="Viability score"))

    with col_sim_table:
        card_header("Shift", "Score changes")
        delta_df = pd.DataFrame({
            "Business": cats,
            "Current": cur_vals,
            "Simulated": sim_vals,
            "Shift": [s - c for c, s in zip(cur_vals, sim_vals)],
        })
        st.markdown(render_custom_table(
            delta_df,
            formats={'Current': '{:.0f}', 'Simulated': '{:.0f}', 'Shift': '{:+.1f}'},
            align={'Current': 'right', 'Simulated': 'right', 'Shift': 'right'},
            column_styles={'Shift': lambda v: f'color:{GREEN if v > 0.05 else (RED if v < -0.05 else INK2)}; font-weight:600'},
        ), unsafe_allow_html=True)


# ===========================================================================
# TAB 6 — PEER GAPS
# ===========================================================================
with tab6:
    card_header("Peer comparison", f"What places like {selected_loc} actually support",
                "No model predictions here — a direct comparison against the 8 most similar "
                "localities by infrastructure and rent. A positive gap means peers sustain "
                "more of that business than exist here.")

    if not neighbors or "restaurant_gap" not in df.columns:
        st.info("Run `scripts/10_similarity.py` to generate the similarity and gap analysis.")
    else:
        col_g1, col_g2 = st.columns([1, 1.4])

        with col_g1:
            card_header("Nearest peers", "Most similar localities")
            peers = neighbors.get(selected_loc, [])
            if peers:
                peer_rows = []
                for p in peers:
                    prow = df[df['name'] == p['name']]
                    peer_rows.append({
                        "Locality": p['name'],
                        "Zone": p['zone'],
                        "Foot traffic": float(prow['overall_footfall'].iloc[0]) if not prow.empty else 0,
                        "Rent / sq ft": float(prow['est_rent_sqft'].iloc[0]) if not prow.empty else 0,
                    })
                st.markdown(render_custom_table(
                    pd.DataFrame(peer_rows),
                    formats={"Foot traffic": '{:.0f}', "Rent / sq ft": '₹{:,.0f}'},
                    align={"Foot traffic": 'right', "Rent / sq ft": 'right'},
                ), unsafe_allow_html=True)
                st.caption("Ranked by similarity of raw infrastructure and rent (standardized k-NN).")
            else:
                st.warning("No peer data for this locality.")

        with col_g2:
            card_header("Supply check", "Peer average vs what exists here")
            gap_view = view_toggle("view_gap", ["Dumbbell", "Bars"])
            g_cats, g_peer, g_here = [], [], []
            for bt in BUSINESS_TYPES:
                exp_col, cnt_col = f"{bt}_expected_count", f"{bt}_count"
                if exp_col not in df.columns:
                    continue
                g_cats.append(bt.replace('_', ' ').title())
                g_peer.append(float(loc_data.get(exp_col, 0)))
                g_here.append(float(loc_data.get(cnt_col, 0)))
            plot(paired_chart(g_cats, g_peer, g_here, "Peer average", selected_loc,
                              NEUTRAL, MARIGOLD, "Bars" if gap_view == "Bars" else "Dumbbell",
                              height=450, x_title="Businesses within 800 m"))

        card_header("Takeaways", "What the peer comparison suggests")
        insights = []
        for bt in BUSINESS_TYPES:
            gap_col = f"{bt}_gap"
            if gap_col not in df.columns:
                continue
            gap = float(loc_data.get(gap_col, 0))
            actual = float(loc_data.get(f"{bt}_count", 0))
            expected = float(loc_data.get(f"{bt}_expected_count", 0))
            reliable = gap_report.get(bt, {}).get('beats_baseline', False)
            insights.append((gap, bt, actual, expected, reliable))

        insights.sort(reverse=True)
        for gap, bt, actual, expected, reliable in insights[:5]:
            label = bt.replace('_', ' ').title()
            flag = "" if reliable else " *(weak signal — peer averages barely beat a global mean for this type)*"
            if gap >= 1:
                st.markdown(f"- **{label}**: similar localities support **~{expected:.0f}**, this one has "
                            f"**{actual:.0f}** → potential room for **~{gap:.0f} more**{flag}")
            elif gap <= -1:
                st.markdown(f"- **{label}**: this locality already has **{actual:.0f}** vs **~{expected:.0f}** "
                            f"among peers → crowded relative to its profile{flag}")
            else:
                st.markdown(f"- **{label}**: supply (~{actual:.0f}) is in line with similar localities{flag}")

        if gap_report:
            n_ok = sum(1 for r in gap_report.values() if r.get('beats_baseline'))
            st.caption(
                f"Method check: leave-one-out validation shows peer averages predict actual business "
                f"counts better than a global mean for {n_ok}/{len(gap_report)} business types. "
                f"Counts come from OpenStreetMap and may undercount real businesses."
            )


# ===========================================================================
# TAB 7 — REPORT
# ===========================================================================
with tab7:
    card_header("Take it with you", f"Download the {selected_loc} report",
                "A structured PDF for one business category in this locality — the same "
                "numbers, charts and caveats the site shows, in plain English. If you have "
                "a what-if scenario running in Simulate, it is included and clearly marked.")

    rep_cat_label = st.selectbox(
        "Business category for the report",
        [bt.replace('_', ' ').title() for bt in BUSINESS_TYPES],
        key="report_bt",
    )
    rep_cat = rep_cat_label.lower().replace(' ', '_')

    # Current predictions for every category
    x_now = pd.DataFrame([loc_data[feature_cols].fillna(0)])
    rep_preds = {bt: float(np.clip(m.predict(x_now)[0], 0, 99)) for bt, m in models.items()}

    # Detect a running what-if scenario (sliders changed in the Simulate tab)
    sim_feats = ['railway_stations', 'metro_stations', 'bus_stops', 'parking_lots',
                 'offices', 'malls', 'est_rent_sqft', 'colleges', 'schools',
                 'hospitals', 'tourist_spots']
    changes = []
    for feat in sim_feats:
        if feat not in feature_cols:
            continue
        sim_val = st.session_state.get(f"sim_{feat}")
        cur_val = float(loc_data.get(feat, 0))
        if sim_val is not None and abs(float(sim_val) - cur_val) > 1e-9:
            changes.append((feat, cur_val, float(sim_val)))

    sim_state = None
    if changes:
        rep_sim_row = loc_data[feature_cols].fillna(0).copy()
        for feat, _, sim_val in changes:
            rep_sim_row[feat] = sim_val
        for score_name, score_val in compute_footfall_scores(rep_sim_row, df).items():
            if score_name in rep_sim_row.index:
                rep_sim_row[score_name] = score_val
        x_rep_sim = pd.DataFrame([rep_sim_row])
        sim_state = {
            "changes": changes,
            "sim_predictions": {bt: float(np.clip(m.predict(x_rep_sim)[0], 0, 99))
                                for bt, m in models.items()},
        }
        st.info(f"A what-if scenario with {len(changes)} adjusted "
                f"criteri{'on' if len(changes) == 1 else 'a'} is active — it will be "
                f"included in the report as its own section.")
    else:
        st.caption("No what-if scenario active. Adjust sliders in Simulate to include one.")

    # Preview of the verdict the report will carry
    rep_score = rep_preds.get(rep_cat, 0)
    rep_band = "Strong" if rep_score >= 60 else ("Moderate" if rep_score >= 35 else "Weak")
    p1, p2, p3 = st.columns(3)
    p1.markdown(f'<div class="metric-card"><div class="metric-title">Viability</div>'
                f'<div class="metric-value">{rep_score:.0f}/100</div></div>', unsafe_allow_html=True)
    p2.markdown(f'<div class="metric-card"><div class="metric-title">Signal</div>'
                f'<div class="metric-value">{rep_band}</div></div>', unsafe_allow_html=True)
    p3.markdown(f'<div class="metric-card"><div class="metric-title">Competitors</div>'
                f'<div class="metric-value">{loc_data.get(f"{rep_cat}_count", 0):.0f}</div></div>',
                unsafe_allow_html=True)

    try:
        pdf_bytes = build_report(
            loc_data=loc_data, df=df, category=rep_cat, cat_label=rep_cat_label,
            predictions=rep_preds, confidence=confidence, gap_report=gap_report,
            neighbors=neighbors, business_types=BUSINESS_TYPES, sim_state=sim_state,
        )
        st.download_button(
            f"Download PDF — {rep_cat_label} in {selected_loc}",
            data=pdf_bytes,
            file_name=f"locality-report-{selected_loc.lower().replace(' ', '-')}-{rep_cat}.pdf",
            mime="application/pdf",
            type="primary",
        )
        st.caption("Covers: the locality · why it works · footfall, rush hours and peak time · "
                   "competition · the statistical approach · approvals · how to start · "
                   "an honest recommendation.")
    except Exception as e:
        st.error(f"Couldn't build the report: {e}")
