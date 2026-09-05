from app import signals


def test_classify_funding():
    assert signals.classify_signal("Bitpanda raises $50M Series C") == "funding"


def test_classify_regulatory():
    assert signals.classify_signal("Nium granted e-money license in Singapore") == "regulatory"


def test_classify_partnership():
    assert signals.classify_signal("Wise partners with Mastercard") == "partnership"


def test_classify_acquisition():
    assert signals.classify_signal("dLocal acquires payment startup") == "acquisition"


def test_classify_other_for_unrelated_headline():
    assert signals.classify_signal("Random unrelated headline about weather") == "other"


def test_diffing_only_flags_genuinely_new_signals(tmp_path, monkeypatch):
    state_file = tmp_path / "signal_state.json"
    monkeypatch.setattr(signals, "STATE_PATH", str(state_file))

    companies = [{"company_name": "TestCo"}]

    first_call_results = [{"title": "TestCo raises Series C", "link": "http://a.com/1", "published": "d1", "category": "funding"}]
    monkeypatch.setattr(signals, "fetch_signals", lambda name, max_results=5: first_call_results)
    round1 = signals.check_for_new_signals(companies)
    assert "TestCo" in round1
    assert len(round1["TestCo"]) == 1

    second_call_results = first_call_results + [
        {"title": "TestCo granted new license", "link": "http://a.com/2", "published": "d2", "category": "regulatory"}
    ]
    monkeypatch.setattr(signals, "fetch_signals", lambda name, max_results=5: second_call_results)
    round2 = signals.check_for_new_signals(companies)
    assert len(round2["TestCo"]) == 1  # only the genuinely new one
    assert round2["TestCo"][0]["link"] == "http://a.com/2"

    round3 = signals.check_for_new_signals(companies)
    assert round3 == {}  # nothing new since round 2


def test_fetch_signals_returns_empty_list_on_network_failure(monkeypatch):
    def raise_error(*args, **kwargs):
        raise ConnectionError("no network")

    monkeypatch.setattr(signals.requests, "get", raise_error)
    assert signals.fetch_signals("AnyCompany") == []


def test_load_state_recovers_from_corrupted_state_file(tmp_path, monkeypatch):
    """Regression test: check_signals.py runs unattended via cron, so a
    corrupted/truncated signal_state.json (e.g. a crash mid-write)
    must not permanently crash every future run."""
    state_file = tmp_path / "signal_state.json"
    state_file.write_text("{this is not valid json")
    monkeypatch.setattr(signals, "STATE_PATH", str(state_file))

    result = signals._load_state()
    assert result == {}


def test_load_state_returns_empty_dict_when_file_missing(tmp_path, monkeypatch):
    state_file = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(signals, "STATE_PATH", str(state_file))

    assert signals._load_state() == {}
