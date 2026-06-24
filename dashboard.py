"""
GTM Terminal — Bloomberg-terminal style dashboard for the outbound engine.

Same dark-navy, data-dense aesthetic as the EKA SOH dashboard redesign,
retargeted to GTM lead intelligence instead of battery telemetry.

Run: streamlit run dashboard.py
"""

import html
from datetime import datetime

import streamlit as st

from app.enrichment import enrich_companies
from app.features import FEATURE_LABELS
from app.personalize import generate_outreach as generate_outreach_template
from app.rag_personalize import generate_outreach_rag
from app.scoring import score_company
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
</style>
""",
    unsafe_allow_html=True,
)


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

ollama_up = check_ollama()
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

    use_rag = st.checkbox("AI-personalized drafts (local Ollama)", value=True)

    run_clicked = st.button("▶ RUN PIPELINE", use_container_width=True)

    st.markdown("---")
    st.markdown(f"MODEL &nbsp; {'🟢 loaded' if model_up else '🔴 run train_model.py'}", unsafe_allow_html=True)
    st.markdown(f"OLLAMA &nbsp; {'🟢 connected' if ollama_up else '🟡 unreachable (will use template)'}", unsafe_allow_html=True)

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
