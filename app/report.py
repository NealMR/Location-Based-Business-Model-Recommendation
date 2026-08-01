"""
report.py
---------
Builds the downloadable locality report: a structured PDF for one locality and
one business category, generated in real time from the same data the site
shows — including any what-if scenario the user has running.
"""

import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF

# Site identity, carried into print
INK = "#152238"
INK2 = "#5B6779"
MUTED = "#8A94A6"
LINE = "#E4E8EF"
TEAL = "#0891B2"
MARIGOLD = "#B45309"
NEUTRAL = "#94A3B8"

RUSH_WINDOWS = {
    "Morning": "roughly 7-11 am (commute and school hours)",
    "Office hours": "roughly 11 am-5 pm (working crowd)",
    "Evening": "roughly 5-10 pm (leisure and shopping)",
    "Weekend": "Saturday-Sunday daytime",
}

# Licences and approvals commonly needed in Mumbai, by category.
# Generic guidance — the report tells the reader to verify with the
# municipal corporation.
BASE_APPROVALS = [
    "Shops & Establishment registration (municipal corporation)",
    "GST registration",
    "Trade licence from the local municipal corporation",
]
EXTRA_APPROVALS = {
    "restaurant": ["FSSAI food licence", "Health/trade NOC", "Fire safety NOC"],
    "cafe": ["FSSAI food licence", "Health/trade NOC"],
    "bar": ["FSSAI food licence", "Liquor licence (State Excise)", "Fire safety NOC"],
    "night_club": ["Liquor licence (State Excise)", "Fire safety NOC",
                   "Police performance/entertainment licence"],
    "gym": ["Fire safety NOC"],
    "lodging": ["Fire safety NOC", "Tourism registration", "Police intimation"],
    "pharmacy": ["Drug licence (FDA Maharashtra)", "Registered pharmacist requirement"],
    "school": ["Education department approvals (for formal schooling)"],
    "beauty_salon": ["Health/trade NOC"],
    "store": [],
}


def _tx(s):
    """Keep text safe for the PDF's core (latin-1) fonts."""
    return (str(s).replace("₹", "Rs. ").replace("—", "-")
            .replace("–", "-").replace("→", "->").replace("’", "'"))


def _fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _style_ax(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(LINE)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="x", color=LINE, linewidth=0.6)
    ax.set_axisbelow(True)


def viability_chart(labels, values, highlight_label):
    order = np.argsort(values)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    colors = [MARIGOLD if l == highlight_label else TEAL for l in labels]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    ax.barh(labels, values, color=colors, height=0.55)
    for i, v in enumerate(values):
        ax.text(v + 1, i, f"{v:.0f}", va="center", fontsize=7.5, color=INK2)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Viability score (0-100)", fontsize=8, color=INK2)
    _style_ax(ax)
    return _fig_png(fig)


def footfall_chart(windows, values, peak):
    colors = [MARIGOLD if w == peak else TEAL for w in windows]
    fig, ax = plt.subplots(figsize=(5.6, 2.1))
    ax.bar(windows, values, color=colors, width=0.5)
    for i, v in enumerate(values):
        ax.text(i, v + 2, f"{v:.0f}", ha="center", fontsize=8, color=INK2)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Foot traffic (0-100)", fontsize=8, color=INK2)
    _style_ax(ax)
    ax.grid(axis="y", color=LINE, linewidth=0.6)
    ax.grid(axis="x", visible=False)
    return _fig_png(fig)


def gap_chart(cats, peer_vals, here_vals):
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    y = np.arange(len(cats))
    for i, (a, b) in enumerate(zip(peer_vals, here_vals)):
        ax.plot([a, b], [i, i], color=LINE, linewidth=2, zorder=1)
    ax.scatter(peer_vals, y, s=45, color=NEUTRAL, zorder=2, label="Peer average")
    ax.scatter(here_vals, y, s=45, color=MARIGOLD, zorder=3, label="This locality")
    ax.set_yticks(y, cats)
    ax.set_xlabel("Businesses within 800 m", fontsize=8, color=INK2)
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    _style_ax(ax)
    return _fig_png(fig)


def sim_chart(cats, current, simulated):
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    y = np.arange(len(cats))
    ax.barh(y + 0.19, current, height=0.34, color=NEUTRAL, label="Current")
    ax.barh(y - 0.19, simulated, height=0.34, color=TEAL, label="Simulated")
    ax.set_yticks(y, cats)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Viability score (0-100)", fontsize=8, color=INK2)
    ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    _style_ax(ax)
    return _fig_png(fig)


class ReportPDF(FPDF):
    def __init__(self, locality, category):
        super().__init__(format="A4")
        self.locality = locality
        self.category = category
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 16, 16)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("helvetica", "", 8)
        self.set_text_color(138, 148, 166)
        self.cell(0, 6, _tx(f"Locality report - {self.locality} - {self.category}"),
                  align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-14)
        self.set_font("helvetica", "", 8)
        self.set_text_color(138, 148, 166)
        self.cell(0, 6, f"Page {self.page_no()}", align="C")

    # ---- building blocks ------------------------------------------------
    def section(self, number, title):
        if self.get_y() > 240:
            self.add_page()
        self.ln(4)
        self.set_font("helvetica", "B", 8)
        self.set_text_color(180, 83, 9)  # marigold
        self.cell(0, 5, f"SECTION {number}")
        self.ln(5)
        self.set_font("helvetica", "B", 13)
        self.set_text_color(21, 34, 56)  # ink
        self.cell(0, 7, _tx(title))
        self.ln(9)

    def para(self, text, size=9.5, color=(91, 103, 121)):
        self.set_font("helvetica", "", size)
        self.set_text_color(*color)
        self.multi_cell(0, 5, _tx(text))
        self.ln(1.5)

    def bullet(self, text):
        self.set_font("helvetica", "", 9.5)
        self.set_text_color(91, 103, 121)
        self.set_x(self.l_margin + 3)
        self.multi_cell(0, 5, _tx(f"-  {text}"))
        self.ln(0.5)

    def stat_row(self, pairs):
        """A row of small stat tiles: [(label, value), ...]"""
        w = (self.w - self.l_margin - self.r_margin) / len(pairs)
        y0 = self.get_y()
        for i, (label, value) in enumerate(pairs):
            x = self.l_margin + i * w
            self.set_xy(x, y0)
            self.set_font("helvetica", "", 7.5)
            self.set_text_color(138, 148, 166)
            self.cell(w, 4, _tx(label.upper()))
            self.set_xy(x, y0 + 4.5)
            self.set_font("helvetica", "B", 12)
            self.set_text_color(21, 34, 56)
            self.cell(w, 6, _tx(value))
        self.set_y(y0 + 13)

    def chart(self, png_buf, height=62):
        if self.get_y() + height > 275:
            self.add_page()
        self.image(png_buf, x=self.l_margin, h=height)
        self.ln(3)

    def note(self, text):
        self.set_font("helvetica", "I", 8.5)
        self.set_text_color(138, 148, 166)
        self.multi_cell(0, 4.5, _tx(text))
        self.ln(1.5)


def build_report(*, loc_data, df, category, cat_label, predictions, confidence,
                 gap_report, neighbors, business_types, sim_state=None):
    """
    Assemble the PDF. Returns bytes.

    predictions: {business_type: score} current model estimates for this locality
    sim_state: None, or dict with keys 'changes' [(feature, current, simulated)],
               'sim_predictions' {bt: score}
    """
    loc = loc_data["name"]
    pdf = ReportPDF(loc, cat_label)
    pdf.add_page()

    # ---- Cover block ------------------------------------------------------
    pdf.set_font("helvetica", "B", 22)
    pdf.set_text_color(21, 34, 56)
    pdf.cell(0, 10, "Locality.")
    pdf.ln(11)
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(91, 103, 121)
    pdf.cell(0, 6, _tx(f"Business feasibility report - {cat_label} in {loc}, Mumbai"))
    pdf.ln(6)
    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(138, 148, 166)
    pdf.cell(0, 5, f"Generated {datetime.now():%d %b %Y, %H:%M}"
             + (" - includes a what-if scenario" if sim_state else ""))
    pdf.ln(10)

    score = predictions.get(category, 0)
    band = "Strong" if score >= 60 else ("Moderate" if score >= 35 else "Weak")
    conf = confidence.get(category, {})
    mae = conf.get("cv_mae", 20)

    footfall = float(loc_data.get("overall_footfall", 0))
    rent = float(loc_data.get("est_rent_sqft", 0))
    count = float(loc_data.get(f"{category}_count", 0))
    expected = float(loc_data.get(f"{category}_expected_count", count))
    gap = float(loc_data.get(f"{category}_gap", 0))
    tag = str(loc_data.get(f"{category}_market_tag", "Unknown"))

    pdf.stat_row([
        ("Viability", f"{score:.0f}/100 ({band})"),
        ("Foot traffic", f"{footfall:.0f}/100"),
        ("Rent", f"Rs. {rent:,.0f}/sq ft"),
        ("Competitors", f"{count:.0f} nearby"),
    ])
    pdf.ln(2)
    pdf.note(f"Every score in this report carries a typical error of about "
             f"+/-{mae:.0f} points (measured by spatial cross-validation). "
             f"Read scores as direction, not certainty.")

    # ---- 1. The locality --------------------------------------------------
    pdf.section(1, f"The locality: {loc}")
    zone = loc_data.get("zone", "-")
    cluster = loc_data.get("cluster_label", "-")
    pdf.para(f"{loc} sits in {zone} and profiles as a {str(cluster).lower()} - "
             f"a label from clustering all 137 localities by traffic, offices, "
             f"education and rent. Commercial rent here runs around Rs. {rent:,.0f} "
             f"per sq ft per month ({str(loc_data.get('rent_tier', '-')).lower()} tier "
             f"for Mumbai). Its overall foot-traffic score is {footfall:.0f} out of 100, "
             f"where 100 is the busiest locality in the city.")

    # ---- 2. Why this locality (or not) -------------------------------------
    pdf.section(2, f"Why {loc} {'works' if score >= 35 else 'is difficult'} for a {cat_label.lower()}")
    comp_labels = [b.replace("_", " ").title() for b in business_types if b in predictions]
    comp_values = [predictions[b] for b in business_types if b in predictions]
    pdf.para(f"The model estimates a viability of {score:.0f}/100 for a "
             f"{cat_label.lower()} here - a {band.lower()} signal. The chart below "
             f"shows how {cat_label.lower()} compares with every other business "
             f"type in this same locality (marigold marks your selection).")
    pdf.chart(viability_chart(comp_labels, comp_values, cat_label), height=66)

    # ---- 3. Footfall, rush hours and peak time ----------------------------
    pdf.section(3, "Footfall, rush hours and peak time")
    windows = list(RUSH_WINDOWS.keys())
    keys = ["morning_footfall", "office_hr_footfall", "evening_footfall", "weekend_footfall"]
    vals = [float(loc_data.get(k, 0)) for k in keys]
    peak_idx = int(np.argmax(vals))
    peak = windows[peak_idx]
    second = windows[int(np.argsort(vals)[-2])]
    pdf.para(f"Foot traffic in {loc} peaks during the {peak.lower()} window - "
             f"{RUSH_WINDOWS[peak]} - scoring {vals[peak_idx]:.0f}/100. The second "
             f"busiest window is {second.lower()}. Plan staffing, stock and opening "
             f"hours around these two windows first.")
    pdf.chart(footfall_chart(windows, vals, peak), height=48)
    pdf.note("These scores are derived from infrastructure (stations, offices, malls, "
             "colleges, tourist spots) - they estimate rhythm, not exact visitor counts.")

    # ---- 4. Competition ----------------------------------------------------
    pdf.section(4, "Competition in the area")
    gap_text = (f"about {gap:.0f} fewer than comparable localities support - room to enter"
                if gap >= 1 else
                (f"about {abs(gap):.0f} more than comparable localities support - a crowded market"
                 if gap <= -1 else "roughly in line with comparable localities"))
    pdf.para(f"OpenStreetMap records {count:.0f} {cat_label.lower()}(s) within 800 m of "
             f"{loc}'s centre. The 8 localities most similar to {loc} (by infrastructure "
             f"and rent) average {expected:.0f} - so this locality has {gap_text}. "
             f"The market screener tags this combination '{tag}'.")
    peers = neighbors.get(loc, [])[:8]
    if peers:
        pdf.para("Most similar localities: " + ", ".join(p["name"] for p in peers) + ".")
    g_cats, g_peer, g_here = [], [], []
    for bt in business_types:
        if f"{bt}_expected_count" in loc_data.index:
            g_cats.append(bt.replace("_", " ").title())
            g_peer.append(float(loc_data.get(f"{bt}_expected_count", 0)))
            g_here.append(float(loc_data.get(f"{bt}_count", 0)))
    if g_cats:
        pdf.chart(gap_chart(g_cats, g_peer, g_here), height=66)
    reliable = gap_report.get(category, {}).get("beats_baseline", False)
    if not reliable:
        pdf.note(f"Honesty note: for {cat_label.lower()}, the peer-average method only "
                 f"barely beats a citywide average in validation - treat the gap "
                 f"figure as a weak signal.")

    # ---- 5. What-if scenario (only if one is running) ----------------------
    section_n = 5
    if sim_state and sim_state.get("changes"):
        pdf.section(section_n, "Your what-if scenario")
        pdf.para("This report includes a simulation you configured on the site. "
                 "The following criteria were changed from today's real values:")
        for feat, cur, sim in sim_state["changes"]:
            pdf.bullet(f"{feat.replace('_', ' ').title()}: {cur:,.0f} -> {sim:,.0f}")
        sim_preds = sim_state.get("sim_predictions", {})
        if sim_preds:
            s_cats = [b.replace("_", " ").title() for b in business_types if b in sim_preds]
            s_cur = [predictions.get(b, 0) for b in business_types if b in sim_preds]
            s_sim = [sim_preds[b] for b in business_types if b in sim_preds]
            pdf.chart(sim_chart(s_cats, s_cur, s_sim), height=66)
            sim_score = sim_preds.get(category, score)
            pdf.para(f"Under this scenario, the {cat_label.lower()} estimate moves from "
                     f"{score:.0f} to {sim_score:.0f}. Remember: this simulates the model's "
                     f"reaction, not a guaranteed real-world outcome.")
        section_n += 1

    # ---- Statistical approach ----------------------------------------------
    pdf.section(section_n, "The statistical approach, in plain English")
    best_model = conf.get("best_model", "a regression model")
    beats = conf.get("beats_baseline", False)
    pdf.para("How these numbers are made: we collect infrastructure counts for 137 "
             "Mumbai localities from OpenStreetMap (stations, offices, schools, malls, "
             "hospitals and more), estimate commercial rent from government Ready "
             "Reckoner rates, and score foot traffic from that infrastructure. "
             "A machine-learning model then estimates business viability, and a "
             "separate peer-comparison method checks supply gaps against the most "
             "similar localities.")
    pdf.bullet(f"Model used for {cat_label.lower()}: {best_model}, tested by holding out "
               f"entire geographic zones (spatial cross-validation).")
    pdf.bullet(f"Typical error: +/-{mae:.0f} points on the 0-100 scale"
               + (", and it beats a naive baseline." if beats
                  else " - and it does NOT clearly beat a naive baseline, so lean on "
                       "the competition figures more than the score."))
    pdf.bullet("Business counts come from OpenStreetMap and may undercount "
               "small or unregistered businesses.")
    pdf.bullet("Revenue-style figures on the site are rough scenarios (rent-only costs), "
               "deliberately excluded from this report's recommendation.")
    section_n += 1

    # ---- How to start + approvals ------------------------------------------
    pdf.section(section_n, f"How to start a {cat_label.lower()} here")
    tier = str(loc_data.get("rent_tier", "moderate")).lower()
    pdf.para(f"A practical starting sequence, grounded in this locality's data:")
    pdf.bullet(f"Visit during the {peak.lower()} window ({RUSH_WINDOWS[peak]}) - that is "
               f"when this locality is busiest and when your trade would concentrate.")
    pdf.bullet(f"Budget for {tier}-tier rent (around Rs. {rent:,.0f}/sq ft/month). "
               f"Negotiate lease terms before fit-out.")
    if count > 0:
        pdf.bullet(f"Study the {count:.0f} existing competitor(s) within 800 m - price "
                   f"points, footfall timing, and what they don't offer.")
    else:
        pdf.bullet("No mapped competitors within 800 m - validate that this reflects "
                   "low competition rather than low demand before committing.")
    pdf.bullet("Secure approvals before signing:")
    for item in BASE_APPROVALS + EXTRA_APPROVALS.get(category, []):
        pdf.bullet("   " + item)
    pdf.note("Approvals vary by ward and change over time - confirm the current list "
             "with the municipal corporation (BMC/NMMC/TMC) before committing funds.")
    section_n += 1

    # ---- Recommendation ------------------------------------------------------
    pdf.section(section_n, "Our honest recommendation")
    if band == "Strong" and gap >= 1:
        verdict = (f"Worth pursuing. The model rates {cat_label.lower()} viability "
                   f"{score:.0f}/100 here and similar localities support more such "
                   f"businesses than currently exist - both signals point the same way.")
    elif band == "Strong" and gap <= -1:
        verdict = (f"Viable, but crowded. The viability score is strong ({score:.0f}/100), "
                   f"yet {loc} already holds more {cat_label.lower()}s than its peers. "
                   f"Enter only with clear differentiation.")
    elif band == "Moderate":
        verdict = (f"Proceed with caution. A {score:.0f}/100 score is middling, and with "
                   f"a typical error of +/-{mae:.0f} points it could be either side of "
                   f"average. Spend time on the ground before committing.")
    else:
        verdict = (f"Reconsider. The model rates {cat_label.lower()} viability just "
                   f"{score:.0f}/100 in {loc}, and nothing in the competition data "
                   f"offsets it. Consider a different category here or a different "
                   f"locality for this category.")
    pdf.para(verdict, size=10, color=(21, 34, 56))

    # Alternatives if weak
    via_col = f"{category}_viability_norm"
    tag_col = f"{category}_market_tag"
    if band != "Strong" and via_col in df.columns and tag_col in df.columns:
        alts = df[(df[tag_col] == "Blue Ocean") & (df["name"] != loc)]
        alts = alts.nlargest(3, via_col)
        if len(alts):
            pdf.para(f"If the category matters more than the location, the strongest "
                     f"underserved localities for a {cat_label.lower()} right now are: "
                     + ", ".join(f"{r['name']} ({r[via_col]:.0f}/100)"
                                 for _, r in alts.iterrows()) + ".")
    pdf.note("This report is generated from public data and statistical models. It is "
             "a screening tool - not a substitute for site visits, local expertise, "
             "or professional financial advice.")

    return bytes(pdf.output())
