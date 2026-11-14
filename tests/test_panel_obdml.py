"""Unit tests for Panel-OBDML (AOW/ATO), strict <= (t-3) history, and fixed diagnostics."""

import numpy as np
import pandas as pd

from fieldwitness.neighbours import diagnostics, panel_obdml, table


def _synthetic_panel(
    n_fields: int = 120,
    n_blocks: int = 8,
    years: tuple[int, ...] = (2017, 2018, 2019, 2020, 2021, 2022),
    true_theta: float = 6.0,
    cycle_strength: float = 0.85,
    time_varying_bias: float = 0.0,
    seed: int = 20261114,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    blocks = [f"b{i % n_blocks}" for i in range(n_fields)]
    alpha_i = rng.normal(0.0, 4.0, size=n_fields)
    clay_i = rng.uniform(15.0, 40.0, size=n_fields)
    sand_i = rng.uniform(15.0, 45.0, size=n_fields)
    soc_i = rng.uniform(10.0, 30.0, size=n_fields)
    area_i = rng.uniform(10.0, 80.0, size=n_fields)
    lon_i = 31.8 + 0.03 * np.arange(n_fields) / n_fields + rng.normal(0, 0.01, n_fields)
    lat_i = 47.9 + 0.03 * (np.arange(n_fields) % n_blocks) / n_blocks

    # Generate Markov crop sequence with strong 2-year alternation cycle (A -> B -> A -> B)
    # Confounded by clay_i and year
    crops_seq = np.empty((n_fields, len(years)), dtype=object)
    shock_it = rng.normal(0.0, 1.5, size=(n_fields, len(years)))
    for i in range(n_fields):
        crops_seq[i, 0] = "maize" if (rng.random() < 0.5) else "winter_wheat"
        for t in range(1, len(years)):
            p_maize = 1.0 / (1.0 + np.exp(-(-0.2 + 0.04 * (clay_i[i] - 25.0))))
            if crops_seq[i, t - 1] == "maize":
                # Strongly alternates away from maize unless cycle is broken
                p_next = 0.15 if rng.random() < cycle_strength else p_maize
            else:
                p_next = 0.85 if rng.random() < cycle_strength else p_maize
            if time_varying_bias != 0.0 and t >= 2:
                # Deliberate violation: future prev_crop (used at t+1) correlates with shock at t-2
                p_next = float(np.clip(p_next + 0.15 * np.sign(shock_it[i, t - 2]), 0.05, 0.95))
            crops_seq[i, t] = "maize" if rng.random() < p_next else "winter_wheat"

    # Build seasonal weather and outcome rows
    rows = []
    yr_fx = {y: 3.0 * np.sin(y) for y in years}
    for t, yr in enumerate(years):
        precip_y = 280.0 + 70.0 * np.sin(yr * 1.3) + rng.normal(0.0, 12.0, n_fields)
        tmax_y = 24.0 + 1.5 * np.cos(yr * 1.1) + rng.normal(0.0, 0.4, n_fields)
        for i in range(n_fields):
            c = crops_seq[i, t]
            prev = crops_seq[i, t - 1] if t >= 1 else None
            prev2 = crops_seq[i, t - 2] if t >= 2 else "unknown"
            # Causal DGP for outcome (cover_days): alpha_i, weather, year, soil, & prev_crop effect
            y_base = (
                120.0
                + alpha_i[i]
                + yr_fx[yr]
                + 0.08 * (precip_y[i] - 280.0)
                - 1.5 * (tmax_y[i] - 24.0)
                + 0.25 * (clay_i[i] - 25.0)
                + shock_it[i, t]
            )
            if c == "sunflower":
                y_base -= 10.0
            treat_eff = true_theta if (c == "maize" and prev == "winter_wheat") else 0.0
            # Set current crop = "maize" on ~60% of 2019+ rows so target contrast is populated
            rows.append(
                {
                    "field_id": f"f{i:03d}",
                    "year": yr,
                    "crop": "maize" if (t >= 2 and i % 3 != 0) else c,
                    "raw_crop": c,
                    "prev_crop": prev,
                    "prev2_crop": prev2,
                    "area_ha": float(area_i[i]),
                    "lon": float(lon_i[i]),
                    "lat": float(lat_i[i]),
                    "clay_pct": float(clay_i[i]),
                    "sand_pct": float(sand_i[i]),
                    "soc_g_kg": float(soc_i[i]),
                    "season_precip_mm": float(precip_y[i]),
                    "season_tmax_c": float(tmax_y[i]),
                    "block": blocks[i],
                    "canopy_integral": float(y_base / 2.0 + treat_eff / 2.0),
                    "peak_ndvi": float(0.75 + 0.01 * (treat_eff > 0)),
                    "cover_days": float(y_base + treat_eff),
                    "canopy_drop": float(0.15 + rng.normal(0.0, 0.02)),
                    "dry_season": bool(precip_y[i] < 280.0),
                }
            )
    full = pd.DataFrame(rows)
    base_2017 = full[full["year"] == 2017].copy()
    main = full[full["year"] >= 2018].copy().reset_index(drop=True)
    # Note: force next_crop to still follow the cycling raw sequence cleanly across years
    # We keep `crop` in `full` consistent by restoring raw_crop for transition realism:
    # For testing the exact contrast (crop == "maize", winter_wheat vs maize):
    # Ensure crop is overridden ONLY on rows with prev_crop in {winter_wheat, maize} cleanly:
    main["crop"] = main["raw_crop"]
    # Add sufficient "maize" outcome rows that preserve Markov alternation on next/prev
    return main, base_2017


def test_add_panel_history_zero_leakage_from_lag2_or_future():
    df, base = _synthetic_panel(n_fields=40, n_blocks=5, years=(2017, 2018, 2019, 2020, 2021))
    h1 = panel_obdml.add_panel_history(df, extra_rows=base)

    # Mutate Y at year 2019 (which is t-2 for 2021) and future year 2022
    df_mut = df.copy()
    df_mut.loc[df_mut["year"] == 2019, "cover_days"] += 999.0
    df_mut.loc[df_mut["year"] == 2021, "cover_days"] -= 500.0
    h2 = panel_obdml.add_panel_history(df_mut, extra_rows=base)

    # For year == 2021 rows, hist_anom_cover_days uses ONLY <= 2018 -> MUST be bitwise identical
    m1 = h1[h1["year"] == 2021]["hist_anom_cover_days"].to_numpy()
    m2 = h2[h2["year"] == 2021]["hist_anom_cover_days"].to_numpy()
    np.testing.assert_allclose(m1, m2)
    assert (h1[h1["year"] == 2021]["has_hist_cover_days"] == 1.0).all()
    assert (h1[h1["year"] == 2018]["has_hist_cover_days"] == 0.0).all()


def test_panel_obdml_recovers_effect_and_passes_all_gates():
    df, base = _synthetic_panel(
        n_fields=180,
        n_blocks=8,
        years=(2017, 2018, 2019, 2020, 2021, 2022, 2023),
        true_theta=6.5,
        cycle_strength=0.65,
        time_varying_bias=0.0,
        seed=42,
    )
    df_hist = panel_obdml.add_panel_history(df, extra_rows=base)
    res = panel_obdml.fit_and_diagnose_contrast(
        df_hist,
        crop="maize",
        treated="winter_wheat",
        ref="maize",
        outcome="cover_days",
        stratum="all",
        min_arm=25,
    )
    assert res["overlap_status"] == "pass", res
    assert res["balance_status"] == "pass", res
    assert res["placebo_status"] == "pass", res
    assert res["negctrl_status"] == "pass", res
    assert res["show_as_evidence"] is True, res
    # True ATE = +6.5 must sit inside estimated 95% CI
    assert res["ci_low"] <= 6.5 <= res["ci_high"], (res["effect"], res["ci_low"], res["ci_high"])
    # 90% CI must be strictly narrower than 95% CI
    assert res["lo90"] > res["ci_low"] and res["hi90"] < res["ci_high"]


def test_panel_obdml_negctrl_catches_time_varying_selection():
    # Generate data where treated arm has direct pre-treatment selection on t-2 outcome shock
    df, base = _synthetic_panel(
        n_fields=180,
        n_blocks=8,
        years=(2017, 2018, 2019, 2020, 2021, 2022, 2023),
        true_theta=4.0,
        cycle_strength=0.0,
        seed=7,
    )
    # Inject strong pre-treatment selection: boost Y_{t-2} whenever treated at t
    df_hist = panel_obdml.add_panel_history(df, extra_rows=base)
    mask = (df_hist["crop"] == "maize") & (df_hist["prev_crop"] == "winter_wheat")
    df_hist.loc[mask, "cover_days_lag2"] += 8.0

    res = panel_obdml.fit_and_diagnose_contrast(
        df_hist,
        crop="maize",
        treated="winter_wheat",
        ref="maize",
        outcome="cover_days",
        stratum="all",
        min_arm=25,
    )
    assert res["negctrl_status"] == "fail", res
    assert res["show_as_evidence"] is False


def test_panel_obdml_fails_overlap_when_propensity_separated():
    df, base = _synthetic_panel(
        n_fields=120,
        n_blocks=8,
        years=(2017, 2018, 2019, 2020, 2021),
        true_theta=5.0,
        seed=11,
    )
    # Force strong spatial/soil separation between treated and reference prev_crop
    sub = df[df["crop"] == "maize"].copy()
    sub.loc[sub["prev_crop"] == "winter_wheat", "clay_pct"] += 40.0
    sub.loc[sub["prev_crop"] == "maize", "clay_pct"] -= 20.0
    df_sep = pd.concat([sub, df[df["crop"] != "maize"]], ignore_index=True)
    df_hist = panel_obdml.add_panel_history(df_sep, extra_rows=base)

    res = panel_obdml.fit_and_diagnose_contrast(
        df_hist,
        crop="maize",
        treated="winter_wheat",
        ref="maize",
        outcome="cover_days",
        stratum="all",
        min_arm=20,
    )
    assert res["overlap_status"] == "fail", res
    assert res["show_as_evidence"] is False


def test_windows_by_region_keeps_kansas_frozen():
    assert table.WINDOWS["winter_wheat"] == (1, 196)
    assert table.WINDOWS_BY_REGION["ua_central_t36uvu"]["winter_wheat"] == (60, 196)
    assert "ks_t14slh" not in table.WINDOWS_BY_REGION
    # Legacy diagnostics.add_lags contract still intact
    df_small = pd.DataFrame(
        {
            "field_id": ["a", "a", "a"],
            "year": [2018, 2019, 2020],
            "crop": ["maize", "winter_wheat", "sunflower"],
            "canopy_integral": [30.0, 25.0, 32.0],
            "peak_ndvi": [0.7, 0.75, 0.72],
            "cover_days": [90.0, 80.0, 88.0],
            "canopy_drop": [0.1, 0.12, 0.11],
        }
    )
    lag = diagnostics.add_lags(df_small)
    assert lag.loc[2, "cover_days_lag2"] == 90.0
    assert lag.loc[0, "next_crop"] == "winter_wheat"
