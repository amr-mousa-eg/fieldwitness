"""Tests for Grade & Credibility Empirical Validity Check (PLAN.md / DECISIONS.md)."""

import json
from pathlib import Path


def test_grade_validity_results_exist():
    p = Path("results/hindcast/grade_validity.json")
    assert p.exists(), "grade_validity.json must exist in results/hindcast/"
    d = json.loads(p.read_text(encoding="utf-8"))

    # Pre-registration requirements
    assert d["as_of_cutoff"] == "2021-12-31", "Must use strict 2021-12-31 cut-off"
    assert d["scored_seasons"] == "2022-2024"
    assert d["total_scored_field_seasons"] == 463

    # Primary test
    pt = d["primary_test"]
    assert pt["target"] == "forecast_ci_crps (canopy integral)"
    assert pt["comparison"] == "Grade B vs Grade D"
    assert pt["diff_d_minus_b_mean"] is not None
    assert len(pt["diff_d_minus_b_ci95"]) == 2
    # Verify primary test did not pass (CI crosses 0)
    assert pt["diff_d_minus_b_ci95"][0] < 0 < pt["diff_d_minus_b_ci95"][1]
    assert pt["passed"] is False
    assert "DID NOT PASS" in pt["verdict"]

    # Grades sample size and stats
    grades = d["grades"]
    for g in ["B", "C", "D"]:
        assert g in grades
        assert grades[g]["n"] >= 20, f"Grade {g} has n < 20 ({grades[g]['n']})"
        assert grades[g]["too_few_to_judge"] is False
        assert grades[g]["forecast_ci_crps_mean"] > 0
        assert len(grades[g]["forecast_ci_crps_ci95"]) == 2

    # Credibility correlation
    corr = d["credibility_rank_correlation"]
    assert corr["n_field_seasons"] > 400
    assert "spearman_rho_crps" in corr
    assert "p_value_crps" in corr


def test_grade_validity_markdown_report_exists():
    md = Path("results/hindcast/grade_validity.md")
    assert md.exists()
    text = md.read_text(encoding="utf-8")
    assert "2021-12-31" in text
    assert "DID NOT PASS" in text
    assert "Grade B" in text
    assert "Grade D" in text
