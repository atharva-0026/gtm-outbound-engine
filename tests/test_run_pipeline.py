"""
Tests for run_pipeline.load_csv — previously had zero test coverage.
"""
import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from run_pipeline import load_csv, main


def _write_csv(rows, fieldnames):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_loads_well_formed_rows():
    path = _write_csv(
        [{"company_name": "Acme", "employee_count": "100", "regulatory_flags": "crypto,neobank"}],
        ["company_name", "employee_count", "regulatory_flags"],
    )
    companies = load_csv(path)
    assert len(companies) == 1
    assert companies[0]["employee_count"] == 100
    assert companies[0]["regulatory_flags"] == ["crypto", "neobank"]


def test_skips_row_with_empty_employee_count():
    path = _write_csv(
        [
            {"company_name": "GoodCo", "employee_count": "100", "regulatory_flags": ""},
            {"company_name": "BadCo", "employee_count": "", "regulatory_flags": ""},
        ],
        ["company_name", "employee_count", "regulatory_flags"],
    )
    companies = load_csv(path)
    assert len(companies) == 1
    assert companies[0]["company_name"] == "GoodCo"


def test_skips_row_with_non_numeric_employee_count():
    path = _write_csv(
        [{"company_name": "BadCo", "employee_count": "not-a-number", "regulatory_flags": ""}],
        ["company_name", "employee_count", "regulatory_flags"],
    )
    companies = load_csv(path)
    assert companies == []


def test_missing_regulatory_flags_column_defaults_to_empty_list():
    """Regression test: row['regulatory_flags'].split(',') previously
    raised KeyError on a missing column instead of treating it as
    empty — .get() must be used instead."""
    path = _write_csv(
        [{"company_name": "Acme", "employee_count": "50"}],
        ["company_name", "employee_count"],
    )
    companies = load_csv(path)
    assert len(companies) == 1
    assert companies[0]["regulatory_flags"] == []


def test_one_bad_row_does_not_prevent_other_rows_from_loading():
    path = _write_csv(
        [
            {"company_name": "GoodCo1", "employee_count": "100", "regulatory_flags": ""},
            {"company_name": "BadCo", "employee_count": "", "regulatory_flags": ""},
            {"company_name": "GoodCo2", "employee_count": "200", "regulatory_flags": ""},
        ],
        ["company_name", "employee_count", "regulatory_flags"],
    )
    companies = load_csv(path)
    names = [c["company_name"] for c in companies]
    assert names == ["GoodCo1", "GoodCo2"]


def test_main_isolates_one_bad_company_instead_of_crashing_whole_run(tmp_path, monkeypatch, capsys):
    """Regression test: app/main.py's /pipeline endpoint already
    isolates a single bad company (employee_count=-500, valid per
    load_csv's plain int() conversion but rejected later by
    build_features()'s math.log1p()) instead of crashing the whole
    batch. main() here had no such isolation and crashed the entire
    CLI run on one bad row."""
    path = _write_csv(
        [
            {"company_name": "GoodCo1", "employee_count": "100", "regulatory_flags": ""},
            {"company_name": "BadCo", "employee_count": "-500", "regulatory_flags": ""},
            {"company_name": "GoodCo2", "employee_count": "50", "regulatory_flags": ""},
        ],
        ["company_name", "employee_count", "regulatory_flags"],
    )
    monkeypatch.chdir(tmp_path)

    main(path)

    with open(tmp_path / "pipeline_output.json") as f:
        results = json.load(f)
    names = {r["company_name"] for r in results}
    assert names == {"GoodCo1", "GoodCo2"}

    err = capsys.readouterr().err
    assert "BadCo" in err
    assert "employee_count must be non-negative" in err
