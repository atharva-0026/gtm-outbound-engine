"""
Source-level regression tests for dashboard.py. dashboard.py runs as
a Streamlit script (calls st.set_page_config at module level before
most functions are even defined), so it can't be safely imported
directly for unit testing - these tests check the source text instead,
matching the pattern already used elsewhere in this codebase for
Streamlit-script code that isn't directly importable.
"""
import os


def _read_dashboard():
    with open(os.path.join(os.path.dirname(__file__), "..", "dashboard.py")) as f:
        return f.read()


def test_regenerate_draft_updates_email_draft_not_just_widget_state():
    """Regression test: regenerate_draft() previously updated the
    subject_{name}/body_{name} session_state widget keys but never
    updated company_result['email_draft'] itself. Two elements in the
    results expander ('RETRIEVED FACTS', the 'generation: ...' caption)
    read r['email_draft'] directly, not session_state - so after
    clicking Regenerate, those stayed frozen on the previous draft's
    metadata even though the visible subject/body had changed."""
    content = _read_dashboard()
    idx = content.find("def regenerate_draft")
    assert idx != -1, "expected regenerate_draft() in dashboard.py"
    # Search from the function definition to the next top-level def,
    # rather than a fixed-size window - avoids breaking every time a
    # comment near the top of the function changes length.
    next_def_idx = content.find("\ndef ", idx + 1)
    snippet = content[idx: next_def_idx if next_def_idx != -1 else len(content)]
    assert 'company_result["email_draft"] = new_draft' in snippet, (
        "regenerate_draft must update company_result['email_draft'], not just "
        "the subject_{name}/body_{name} session_state keys, so the "
        "'RETRIEVED FACTS' and 'generation: ...' caption (which read "
        "r['email_draft'] directly) stay in sync with what's actually displayed"
    )
