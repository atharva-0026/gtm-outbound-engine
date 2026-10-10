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
    from streamlit.runtime.secrets import StreamlitSecretNotFoundError
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except StreamlitSecretNotFoundError:
    pass  # no secrets.toml locally — fine, Ollama-only is the local default

from app.closed_loop import process_new_signals
from app.enrichment import enrich_companies
from app.features import filter_results, find_duplicate_company_names, results_to_csv, score_tier
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
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0A0E1A; --panel: #111827; --panel-2: #0F1522; --line: #1F2937; --line-2: #2B3647;
    --text: #E5E7EB; --muted: #6B7280; --soft: #9CA3AF;
    --hot: #34D399; --warm: #F59E0B; --cold: #EF4444; --amber: #FBBF24;
}
html, body, [class*="css"] { font-family: 'IBM Plex Mono', monospace !important; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0rem; padding-bottom: 3rem; max-width: 1200px; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0D1220 0%, #0A0E1A 100%); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #10B981, #059669); color: #04130D; border: none;
    font-weight: 700; letter-spacing: 1px; border-radius: 6px; transition: transform .15s, box-shadow .2s;
}
section[data-testid="stSidebar"] .stButton button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px -10px #10B981; color: #04130D; }
.side-brand { display: flex; align-items: center; gap: 10px; margin: 0.25rem 0 1.25rem; }
.side-brand .mark { width: 34px; height: 34px; border-radius: 8px; display: grid; place-items: center; font-size: 18px;
    background: radial-gradient(circle at 30% 30%, #34D399, #065F46); box-shadow: 0 0 18px -4px #34D399; }
.side-brand .name { font-weight: 700; letter-spacing: 1.5px; color: var(--text); font-size: 14px; }
.side-brand .tag { font-size: 10px; color: var(--muted); letter-spacing: 1px; }
.side-label { font-size: 10px; color: var(--muted); letter-spacing: 1.5px; margin: 0.75rem 0 0.25rem; }
.status-line { display: flex; justify-content: space-between; font-size: 12px; color: var(--soft); padding: 4px 0; }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }

.ticker-wrap {
    background: #000000;
    border-bottom: 1px solid var(--line);
    overflow: hidden;
    white-space: nowrap;
    height: 34px;
    display: flex;
    align-items: center;
    margin: 0 -1rem 1.75rem -1rem;
    -webkit-mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
            mask-image: linear-gradient(90deg, transparent, #000 4%, #000 96%, transparent);
}
.ticker-move {
    display: inline-block;
    white-space: nowrap;
    animation: ticker-scroll 30s linear infinite;
    color: var(--amber);
    font-size: 13px;
    letter-spacing: 0.5px;
}
.ticker-wrap:hover .ticker-move { animation-play-state: paused; }
@keyframes ticker-scroll {
    from { transform: translateX(0%); }
    to   { transform: translateX(-50%); }
}

.terminal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 1rem;
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--line);
}
.terminal-title {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: 2px;
    background: linear-gradient(90deg, #E5E7EB 0%, #34D399 120%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
}
.terminal-subtitle { font-size: 12px; color: var(--muted); letter-spacing: 1.5px; margin-top: 2px; }
.terminal-meta { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.chip {
    font-size: 11px; color: var(--soft); background: var(--panel); border: 1px solid var(--line);
    padding: 4px 10px; border-radius: 999px; letter-spacing: 0.5px; white-space: nowrap;
}

.metric-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 1.25rem; }
.metric-box {
    position: relative; overflow: hidden;
    background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px 16px;
}
.metric-box::before { content: ""; position: absolute; left: 0; top: 0; right: 0; height: 2px; background: var(--accent, #374151); }
.metric-label { font-size: 10px; color: var(--muted); letter-spacing: 1.2px; }
.metric-value { font-size: 26px; font-weight: 700; color: var(--text); margin-top: 2px; }
.metric-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

.tier-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--line); margin: 0 0 0.4rem; }
.tier-bar span { display: block; height: 100%; }
.tier-legend { display: flex; gap: 16px; font-size: 11px; color: var(--soft); margin-bottom: 1.5rem; }

.lead-row {
    background: var(--panel);
    border: 1px solid var(--line);
    border-left: 3px solid var(--tier, #374151);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color .2s, transform .15s, background .2s;
}
.lead-row:hover { border-color: var(--line-2); border-left-color: var(--tier, #374151); background: #131B2C; transform: translateX(2px); }
.lead-row-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.lead-rank { color: var(--muted); font-size: 13px; width: 32px; }
.lead-name { font-size: 16px; font-weight: 600; color: var(--text); }
.lead-meta { font-size: 12px; color: var(--muted); }
.lead-score { font-size: 22px; font-weight: 700; }
.lead-driver { font-size: 11px; letter-spacing: 0.5px; }
.tier-badge {
    font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 2px 8px; border-radius: 999px;
    margin-left: 8px; vertical-align: middle;
}

.score-track {
    background: var(--line);
    border-radius: 3px;
    height: 5px;
    width: 100%;
    margin-top: 10px;
    overflow: hidden;
}
.score-fill { height: 5px; border-radius: 3px; }

.shap-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.shap-label { font-size: 12px; color: var(--soft); width: 170px; flex-shrink: 0; }
.shap-track { background: var(--line); height: 8px; flex: 1; border-radius: 4px; position: relative; overflow: hidden; }
.shap-fill { height: 8px; border-radius: 4px; }
.shap-value { font-size: 11px; color: var(--muted); width: 50px; text-align: right; flex-shrink: 0; }

.fact-quote {
    font-size: 12px;
    color: var(--soft);
    border-left: 2px solid #34D39966;
    background: #0F172A;
    border-radius: 0 6px 6px 0;
    padding: 6px 10px;
    margin: 6px 0;
}

.signal-panel {
    background: linear-gradient(180deg, #1C1408 0%, #140F06 100%);
    border: 1px solid #92400E;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 1.2rem;
}
.signal-panel-title { font-size: 12px; color: var(--amber); letter-spacing: 1px; margin-bottom: 8px; }
.signal-item { font-size: 13px; color: var(--text); margin: 6px 0; }
.signal-tag {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 4px;
    margin-right: 6px;
    letter-spacing: 0.5px;
}

.empty-hero {
    text-align: center; padding: 4rem 1rem; border: 1px dashed var(--line-2); border-radius: 12px;
    background: radial-gradient(600px 200px at 50% 0%, #34D39914, transparent 70%);
}
.empty-hero .big { font-size: 42px; margin-bottom: 0.5rem; }
.empty-hero .title { font-size: 16px; color: var(--text); font-weight: 600; letter-spacing: 1px; }
.empty-hero .sub { font-size: 12px; color: var(--muted); margin-top: 6px; }
.results-count { font-size: 11px; color: var(--muted); letter-spacing: 1px; margin: 0.25rem 0 0.75rem; }
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


TIER_COLORS = {"hot": "#34D399", "warm": "#F59E0B", "cold": "#EF4444"}


def score_color(score):
    return TIER_COLORS[score_tier(score)]


def render_ticker(results):
    if not results:
        items = ["RUN PIPELINE TO BEGIN"]
    else:
        items = []
        for r in results:
            top_label = next(iter(r["score_breakdown"]), "—")
            arrow = "▲" if next(iter(r["score_breakdown"].values())) >= 0 else "▼"
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
    # Must also update company_result["email_draft"] itself (not just
    # the two widget-state keys above), since the "RETRIEVED FACTS" and
    # "generation: ..." caption in the results expander read
    # r["email_draft"] directly - not session_state. Without this,
    # clicking Regenerate changed the visible subject/body but left
    # those two elements permanently frozen on the PREVIOUS draft's
    # metadata, misleading the user about where the draft on screen
    # actually came from. company_result is the same dict object
    # stored in st.session_state.results (Python dicts are passed by
    # reference), so mutating it here is visible on the next rerun.
    company_result["email_draft"] = new_draft


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
    st.markdown(
        '<div class="side-brand"><div class="mark">📡</div><div>'
        '<div class="name">GTM TERMINAL</div><div class="tag">OUTBOUND ENGINE</div></div></div>'
        '<div class="side-label">SOURCE</div>',
        unsafe_allow_html=True,
    )
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

    # company_name is used as an implicit unique key throughout this
    # dashboard (session_state keys for email drafts, the by_name
    # lookup in signal re-scoring below). Two companies sharing the
    # same name - realistic for any uploaded CSV, e.g. duplicate rows
    # or two genuinely different companies with the same name - would
    # silently collapse into one entry with no indication anything was
    # lost. Warn instead of letting that happen invisibly.
    if companies:
        duplicate_names = find_duplicate_company_names(companies)
        if duplicate_names:
            st.warning(
                f"⚠️ Duplicate company name(s) found: {', '.join(sorted(duplicate_names))}. "
                "Only one entry per name will be shown in results and email drafts — "
                "rename duplicates in your CSV if they're actually different companies."
            )

    use_rag = st.checkbox("AI-personalized drafts (Ollama/Groq)", value=True)

    run_clicked = st.button("▶ RUN PIPELINE", use_container_width=True)

    st.markdown("---")
    if ollama_up:
        llm_color, llm_status = "#34D399", "Ollama"
    elif groq_ready:
        llm_color, llm_status = "#34D399", "Groq (cloud)"
    else:
        llm_color, llm_status = "#F59E0B", "template only"
    model_color, model_status = ("#34D399", "loaded") if model_up else ("#EF4444", "run train_model.py")
    st.markdown(
        '<div class="side-label">SYSTEM</div>'
        f'<div class="status-line"><span>MODEL</span><span><span class="dot" style="background:{model_color}"></span>{model_status}</span></div>'
        f'<div class="status-line"><span>LLM</span><span><span class="dot" style="background:{llm_color}"></span>{llm_status}</span></div>',
        unsafe_allow_html=True,
    )

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
        <div class="terminal-subtitle">AML / REGTECH OUTBOUND INTELLIGENCE</div>
    </div>
    <div class="terminal-meta">
        <span class="chip">{len(companies)} IN LIST</span>
        <span class="chip">DRAFTS: {'AI' if use_rag else 'TEMPLATE'}</span>
        <span class="chip">LAST RUN: {st.session_state.last_run or '—'}</span>
    </div>
</div>
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
                f'<span class="signal-tag" style="background:{tag_color}22; color:{tag_color};">{html.escape(s["category"].upper())}</span>'
                f'<b>{html.escape(company_name)}</b> — {html.escape(s["title"])}{delta_html}'
                f"</div>"
            )
    panel_html += "</div>"
    st.markdown(panel_html, unsafe_allow_html=True)
    st.caption("Drafts for these accounts were regenerated with the news worked in.")

if not results:
    st.markdown(
        '<div class="empty-hero"><div class="big">📡</div>'
        '<div class="title">NO LEADS SCORED YET</div>'
        '<div class="sub">Pick a lead list in the sidebar and hit ▶ RUN PIPELINE</div></div>',
        unsafe_allow_html=True,
    )
else:
    avg_score = sum(r["icp_score"] for r in results) / len(results)
    tier_counts = {t: sum(1 for r in results if score_tier(r["icp_score"]) == t) for t in TIER_COLORS}
    hot_leads = tier_counts["hot"]

    st.markdown(
        f"""
<div class="metric-row">
    <div class="metric-box" style="--accent:#60A5FA"><div class="metric-label">LEADS SCORED</div><div class="metric-value">{len(results)}</div></div>
    <div class="metric-box" style="--accent:{score_color(avg_score)}"><div class="metric-label">AVG ICP SCORE</div><div class="metric-value">{avg_score:.1f}</div></div>
    <div class="metric-box" style="--accent:{score_color(results[0]['icp_score'])}"><div class="metric-label">TOP SCORE</div><div class="metric-value">{results[0]['icp_score']:.1f}</div><div class="metric-sub">{html.escape(results[0]['company_name'])}</div></div>
    <div class="metric-box" style="--accent:#34D399"><div class="metric-label">HOT LEADS (≥75)</div><div class="metric-value">{hot_leads}</div><div class="metric-sub">{hot_leads / len(results):.0%} of list</div></div>
</div>
<div class="tier-bar">{''.join(f'<span style="width:{tier_counts[t] / len(results) * 100}%;background:{c}"></span>' for t, c in TIER_COLORS.items())}</div>
<div class="tier-legend">{''.join(f'<span><span class="dot" style="background:{c}"></span>{t.upper()} {tier_counts[t]}</span>' for t, c in TIER_COLORS.items())}</div>
""",
        unsafe_allow_html=True,
    )

    # session_state[f"subject_{name}"]/[f"body_{name}"] are always
    # pre-seeded with the generated draft right after scoring (see
    # where results is assigned above), so reading them directly here
    # reflects either the original draft or the user's actual edit -
    # whichever is currently on screen - with no need to distinguish
    # the two cases.
    edited_drafts = {
        r["company_name"]: {
            "subject": st.session_state.get(f"subject_{r['company_name']}"),
            "body": st.session_state.get(f"body_{r['company_name']}"),
        }
        for r in results
    }

    f1, f2, f3 = st.columns([2.2, 1.6, 1.2])
    with f1:
        query = st.text_input("Search", placeholder="🔍  Company, industry or country", label_visibility="collapsed")
    with f2:
        tiers = st.multiselect(
            "Tiers", list(TIER_COLORS), default=list(TIER_COLORS),
            format_func=str.upper, label_visibility="collapsed",
        )
    with f3:
        min_score = st.slider("Min score", 0, 100, 0, label_visibility="collapsed")

    visible = filter_results(results, query=query, min_score=min_score, tiers=tiers)
    rank_of = {r["company_name"]: i for i, r in enumerate(results, start=1)}

    st.download_button(
        f"⬇ Export {len(visible)} lead{'s' if len(visible) != 1 else ''} (CSV)",
        data=results_to_csv(visible, edited_drafts=edited_drafts),
        file_name=f"gtm_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=not visible,
    )
    st.markdown(
        f'<div class="results-count">SHOWING {len(visible)} OF {len(results)} LEADS</div>',
        unsafe_allow_html=True,
    )
    if not visible:
        st.caption("No leads match these filters.")

    for r in visible:
        name = r["company_name"]
        rank = rank_of[name]
        tier = score_tier(r["icp_score"])
        color = score_color(r["icp_score"])
        breakdown = r["score_breakdown"]
        top_label, top_val = next(iter(breakdown.items()))
        arrow = "▲" if top_val >= 0 else "▼"

        st.markdown(
            f"""
<div class="lead-row" style="--tier:{color};">
    <div class="lead-row-top">
        <div style="display:flex; align-items:center; gap:14px;">
            <span class="lead-rank">#{rank}</span>
            <div>
                <span class="lead-name">{html.escape(name)}</span><span class="tier-badge" style="background:{color}22; color:{color};">{tier.upper()}</span>
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
