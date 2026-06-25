"""
GTM Terminal — Bloomberg-terminal style dashboard for the outbound engine.

Same dark-navy, data-dense aesthetic as the EKA SOH dashboard redesign,
retargeted to GTM lead intelligence instead of battery telemetry.

Run: streamlit run dashboard.py
"""

import html
import os
from datetime import datetime

import streamlit as st

# On Streamlit Community Cloud, secrets are configured in the dashboard's
# Settings UI, not as real environment variables. Bridge them into
# os.environ here so app/rag_personalize.py (which doesn't import
# streamlit, by design — it also runs under the CLI and FastAPI) can read
# GROQ_API_KEY the same way locally and in the cloud.
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass  # no secrets.toml locally — fine, Ollama-only is the local default

from app.closed_loop import process_new_signals
from app.enrichment import enrich_companies
from app.features import FEATURE_LABELS
from app.personalize import generate_outreach as generate_outreach_template
from app.rag_personalize import generate_outreach_rag
from app.scoring import score_company
from app.signals import check_for_new_signals
from run_pipeline import load_csv

st.set_page_config(page_title="GTM Terminal", page_icon="📡", layout="wide")

# ---------------------------------------------------------------- styling --

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Mono', monospace !important;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0rem; padding-bottom: 2rem; max-width: 1200px; }

.ticker-wrap {
    background: #000000;
    border-bottom: 1px solid #1F2937;
    overflow: hidden;
    white-space: nowrap;
    height: 34px;
    display: flex;
    align-items: center;
    margin: 0 -1rem 1.5rem -1rem;
}
.ticker-move {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 30s linear infinite;
    color: #FBBF24;
    font-size: 13px;
    letter-spacing: 0.5px;
}
@keyframes ticker-scroll {
    from { transform: translateX(0%); }
    to   { transform: translateX(-50%); }
}

.terminal-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.25rem;
}
.terminal-title {
    font-size: 28px;
    font-weight: 700;
    color: #E5E7EB;
    letter-spacing: 1px;
}
.terminal-subtitle {
    font-size: 13px;
    color: #6B7280;
    margin-top: -8px;
    margin-bottom: 1.2rem;
}
.terminal-meta {
    font-size: 12px;
    color: #6B7280;
    text-align: right;
}

.metric-row { display: flex; gap: 12px; margin-bottom: 1.5rem; }
.metric-box {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 2px;
    padding: 10px 16px;
    flex: 1;
}
.metric-label { font-size: 11px; color: #6B7280; letter-spacing: 0.5px; }
.metric-value { font-size: 22px; font-weight: 600; color: #E5E7EB; }

.lead-row {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 2px;
    padding: 12px 16px;
    margin-bottom: 6px;
}
.lead-row-top { display: flex; align-items: center; justify-content: space-between; }
.lead-rank { color: #6B7280; font-size: 13px; width: 28px; }
.lead-name { font-size: 16px; font-weight: 600; color: #E5E7EB; }
.lead-meta { font-size: 12px; color: #6B7280; }
.lead-score { font-size: 20px; font-weight: 700; }
.lead-driver { font-size: 11px; letter-spacing: 0.5px; }

.score-track {
    background: #1F2937;
    border-radius: 2px;
    height: 5px;
    width: 100%;
    margin-top: 6px;
}
.score-fill { height: 5px; border-radius: 2px; }

.shap-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.shap-label { font-size: 12px; color: #9CA3AF; width: 170px; flex-shrink: 0; }
.shap-track { background: #1F2937; height: 8px; flex: 1; border-radius: 2px; position: relative; }
.shap-fill { height: 8px; border-radius: 2px; }
.shap-value { font-size: 11px; color: #6B7280; width: 50px; text-align: right; flex-shrink: 0; }

.fact-quote {
    font-size: 12px;
    color: #9CA3AF;
    border-left: 2px solid #374151;
    padding-left: 10px;
    margin: 4px 0;
}

.signal-panel {
    background: #1C1408;
    border: 1px solid #92400E;
    border-radius: 2px;
    padding: 12px 16px;
    margin-bottom: 1.2rem;
}
.signal-panel-title { font-size: 12px; color: #FBBF24; letter-spacing: 0.5px; margin-bottom: 6px; }
.signal-item { font-size: 13px; color: #E5E7EB; margin: 4px 0; }
.signal-tag {
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 2px;
    margin-right: 6px;
    letter-spacing: 0.5px;
}
</style>
""",
    unsafe_allow_html=True,
)

SIGNAL_TAG_COLORS = {
    "funding": "#34D399",
    "regulatory": "#60A5FA",
    "partnership": "#A78BFA",
    "acquisition": "#F59E0B",
    "other": "#6B7280",
}


# ---------------------------------------------------------------- helpers --


def score_color(score):
    if score >= 75:
        return "#34D399"
    if score >= 45:
        return "#F59E0B"
    return "#EF4444"


def render_ticker(results):
    if not results:
        items = ["RUN PIPELINE TO BEGIN"]
    else:
        items = []
        for r in results:
            top_label = next(iter(r["score_breakdown"]), "—")
            arrow = "▲" if list(r["score_breakdown"].values())[0] >= 0 else "▼"
            items.append(
                f"{html.escape(r['company_name'].upper())} {r['icp_score']:.1f} "
                f"{arrow} {html.escape(top_label.upper())}"
            )
    content = "   •   ".join(items)
    full = f"{content}   •   {content}"  # duplicated for seamless loop
    st.markdown(
        f'<div class="ticker-wrap"><div class="ticker-move">{full}</div></div>',
        unsafe_allow_html=True,
    )


def check_ollama():
    try:
        import requests

        r = requests.get("http://localhost:11434/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def groq_configured():
    return bool(os.environ.get("GROQ_API_KEY"))


def model_ready():
    try:
        score_company({"company_name": "_probe_", "employee_count": 100, "regulatory_flags": []})
        return True
    except FileNotFoundError:
        return False


def regenerate_draft(company_result, use_rag_flag, name):
    new_draft = (
        generate_outreach_rag(company_result) if use_rag_flag else generate_outreach_template(company_result)
    )
    st.session_state[f"subject_{name}"] = new_draft["subject"]
    st.session_state[f"body_{name}"] = new_draft["body"]


def process_company(raw_company: dict, use_rag: bool) -> dict:
    enriched = enrich_companies([raw_company])[0]
    scored = score_company(enriched)
    draft = generate_outreach_rag(scored) if use_rag else generate_outreach_template(scored)
    return {**scored, "email_draft": draft}


# ------------------------------------------------------------------ state --

if "results" not in st.session_state:
    st.session_state.results = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "new_signals" not in st.session_state:
    st.session_state.new_signals = {}
if "signal_rescore_info" not in st.session_state:
    st.session_state.signal_rescore_info = {}
if "signals_checked_at" not in st.session_state:
    st.session_state.signals_checked_at = None

ollama_up = check_ollama()
groq_ready = groq_configured()
model_up = model_ready()

# --------------------------------------------------------------- sidebar --

with st.sidebar:
    st.markdown("**SOURCE**")
    source_mode = st.radio("source", ["Saved lead list", "Upload CSV"], label_visibility="collapsed")

    if source_mode == "Saved lead list":
        csv_path = st.selectbox("file", ["data/real_leads.csv", "data/sample_leads.csv"], label_visibility="collapsed")
        companies = load_csv(csv_path)
    else:
        uploaded = st.file_uploader("CSV", type="csv", label_visibility="collapsed")
        companies = []
        if uploaded:
            import io

            companies = load_csv(io.StringIO(uploaded.getvalue().decode("utf-8")))

    use_rag = st.checkbox("AI-personalized drafts (Ollama/Groq)", value=True)

    run_clicked = st.button("▶ RUN PIPELINE", use_container_width=True)

    st.markdown("---")
    st.markdown(f"MODEL &nbsp; {'🟢 loaded' if model_up else '🔴 run train_model.py'}", unsafe_allow_html=True)
    if ollama_up:
        llm_status = "🟢 Ollama connected"
    elif groq_ready:
        llm_status = "🟢 Groq connected (cloud)"
    else:
        llm_status = "🟡 no LLM — using template"
    st.markdown(f"LLM &nbsp; {llm_status}", unsafe_allow_html=True)

    st.markdown("---")
    check_signals_clicked = st.button("🔔 CHECK SIGNALS", use_container_width=True)
    if st.session_state.get("signals_checked_at"):
        st.caption(f"Last checked: {st.session_state.signals_checked_at}")

if run_clicked and companies:
    progress = st.progress(0, text="Starting...")
    results = []
    for i, c in enumerate(companies):
        progress.progress((i) / len(companies), text=f"Processing {c['company_name']}... ({i+1}/{len(companies)})")
        results.append(process_company(c, use_rag))
    progress.empty()
    results.sort(key=lambda r: r["icp_score"], reverse=True)
    st.session_state.results = results
    st.session_state.last_run = datetime.now().strftime("%H:%M:%S")
    for r in results:
        st.session_state[f"subject_{r['company_name']}"] = r["email_draft"]["subject"]
        st.session_state[f"body_{r['company_name']}"] = r["email_draft"]["body"]

if check_signals_clicked and companies:
    with st.spinner("Checking public signals (Google News)..."):
        new_signals = check_for_new_signals(companies)
    st.session_state.signals_checked_at = datetime.now().strftime("%H:%M:%S")

    if new_signals:
        by_name = {c["company_name"]: c for c in companies}
        before_scores = {
            name: score_company(enrich_companies([by_name[name]])[0])["icp_score"]
            for name in new_signals
            if name in by_name
        }
        with st.spinner(f"Re-scoring {len(new_signals)} accounts with new signals..."):
            rescored = process_new_signals(companies, new_signals, use_rag=use_rag)

        results_by_name = {r["company_name"]: r for r in st.session_state.results}
        for name, updated in rescored.items():
            updated["score_delta"] = updated["icp_score"] - before_scores.get(name, updated["icp_score"])
            results_by_name[name] = updated
            st.session_state[f"subject_{name}"] = updated["email_draft"]["subject"]
            st.session_state[f"body_{name}"] = updated["email_draft"]["body"]

        st.session_state.results = sorted(results_by_name.values(), key=lambda r: r["icp_score"], reverse=True)
        st.session_state.new_signals = new_signals
        st.session_state.signal_rescore_info = {
            name: {"before": before_scores.get(name), "after": rescored[name]["icp_score"]} for name in rescored
        }
    else:
        st.session_state.new_signals = {}
        st.session_state.signal_rescore_info = {}

results = st.session_state.results

# -------------------------------------------------------------------- ui --

render_ticker(results)

st.markdown(
    f"""
<div class="terminal-header">
    <div>
        <div class="terminal-title">GTM TERMINAL</div>
    </div>
    <div class="terminal-meta">LAST RUN: {st.session_state.last_run or '—'}</div>
</div>
<div class="terminal-subtitle">AML / REGTECH OUTBOUND INTELLIGENCE</div>
""",
    unsafe_allow_html=True,
)

if st.session_state.new_signals:
    panel_html = '<div class="signal-panel"><div class="signal-panel-title">🔔 NEW SIGNALS — RE-SCORED AUTOMATICALLY</div>'
    for company_name, sigs in st.session_state.new_signals.items():
        rescore = st.session_state.signal_rescore_info.get(company_name)
        delta_html = ""
        if rescore and rescore["before"] is not None:
            delta = rescore["after"] - rescore["before"]
            if abs(delta) >= 0.1:
                delta_color = "#34D399" if delta > 0 else "#EF4444"
                delta_html = (
                    f' <span style="color:{delta_color};">'
                    f'({rescore["before"]:.1f} → {rescore["after"]:.1f})</span>'
                )
            else:
                delta_html = ' <span style="color:#6B7280;">(score unchanged)</span>'
        for s in sigs:
            tag_color = SIGNAL_TAG_COLORS.get(s["category"], "#6B7280")
            panel_html += (
                f'<div class="signal-item">'
                f'<span class="signal-tag" style="background:{tag_color}22; color:{tag_color};">{s["category"].upper()}</span>'
                f'<b>{html.escape(company_name)}</b> — {html.escape(s["title"])}{delta_html}'
                f"</div>"
            )
    panel_html += "</div>"
    st.markdown(panel_html, unsafe_allow_html=True)
    st.caption("Drafts for these accounts were regenerated with the news worked in.")

if not results:
    st.info("Select a lead list in the sidebar and click RUN PIPELINE.")
else:
    avg_score = sum(r["icp_score"] for r in results) / len(results)
    hot_leads = sum(1 for r in results if r["icp_score"] >= 75)

    st.markdown(
        f"""
<div class="metric-row">
    <div class="metric-box"><div class="metric-label">LEADS SCORED</div><div class="metric-value">{len(results)}</div></div>
    <div class="metric-box"><div class="metric-label">AVG ICP SCORE</div><div class="metric-value">{avg_score:.1f}</div></div>
    <div class="metric-box"><div class="metric-label">TOP SCORE</div><div class="metric-value">{results[0]['icp_score']:.1f}</div></div>
    <div class="metric-box"><div class="metric-label">HOT LEADS (≥75)</div><div class="metric-value">{hot_leads}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    for rank, r in enumerate(results, start=1):
        name = r["company_name"]
        color = score_color(r["icp_score"])
        breakdown = r["score_breakdown"]
        top_label, top_val = next(iter(breakdown.items()))
        arrow = "▲" if top_val >= 0 else "▼"

        st.markdown(
            f"""
<div class="lead-row">
    <div class="lead-row-top">
        <div style="display:flex; align-items:center; gap:14px;">
            <span class="lead-rank">#{rank}</span>
            <div>
                <span class="lead-name">{html.escape(name)}</span>
                <span class="lead-meta">&nbsp;&nbsp;{html.escape(r.get('industry') or '')} · {html.escape(r.get('country') or '')}</span>
            </div>
        </div>
        <div style="text-align:right;">
            <span class="lead-score" style="color:{color};">{r['icp_score']:.1f}</span>
            <div class="lead-driver" style="color:{color};">{arrow} {html.escape(top_label.upper())}</div>
        </div>
    </div>
    <div class="score-track"><div class="score-fill" style="width:{r['icp_score']}%; background:{color};"></div></div>
</div>
""",
            unsafe_allow_html=True,
        )

        with st.expander(f"Details — {name}"):
            col1, col2 = st.columns([1, 1.4])

            with col1:
                st.markdown("**SHAP BREAKDOWN**")
                max_abs = max(abs(v) for v in breakdown.values()) or 1
                for label, val in breakdown.items():
                    bar_color = "#34D399" if val >= 0 else "#EF4444"
                    width_pct = round(abs(val) / max_abs * 100, 1)
                    st.markdown(
                        f"""
<div class="shap-bar-row">
    <div class="shap-label">{html.escape(label)}</div>
    <div class="shap-track"><div class="shap-fill" style="width:{width_pct}%; background:{bar_color};"></div></div>
    <div class="shap-value">{val:+.2f}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )

                facts = r["email_draft"].get("retrieved_facts")
                if facts:
                    st.markdown("**RETRIEVED FACTS**")
                    for f in facts:
                        st.markdown(f'<div class="fact-quote">{html.escape(f)}</div>', unsafe_allow_html=True)

                st.caption(f"generation: {r['email_draft'].get('generation_method', 'n/a')}")

            with col2:
                st.markdown("**OUTREACH DRAFT** (editable)")
                st.text_input("Subject", key=f"subject_{name}")
                st.text_area("Body", key=f"body_{name}", height=180)

                st.button(
                    "↻ Regenerate",
                    key=f"regen_{name}",
                    on_click=regenerate_draft,
                    args=(r, use_rag, name),
                )
