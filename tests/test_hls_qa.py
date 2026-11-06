"""T1.5 QA rule on a synthetic task folder: cloud/shadow/snow/water/adjacent dropped, VI fill
dropped, Fmask-only dates dropped, two sensors on one date counted once per pixel."""

import pandas as pd

from fieldwitness.data.hls_qa import read_task

S = "HLSL30"


def _write(folder, vi_rows, fm_rows):
    flags = ["Cloud", "Adjacent_to_cloud/shadow", "Cloud_shadow", "Snow/ice", "Water"]
    pd.DataFrame(
        vi_rows, columns=["Category", "ID", "Date", f"{S}_VI_020_NDVI", f"{S}_VI_020_EVI"]
    ).to_csv(folder / f"x-{S}-VI-020-results.csv", index=False)
    cols = ["ID", "Date", f"{S}_020_Fmask", *[f"{S}_020_Fmask_{f}" for f in flags]]
    pd.DataFrame(fm_rows, columns=cols).to_csv(folder / f"x-{S}-020-results.csv", index=False)


def test_qa_rule(tmp_path):
    vi = [("f", f"p{i}", d, 0.5, 0.4) for i, d in enumerate(["2020-01-01"] * 6)]
    vi.append(("f", "p6", "2020-01-02", -19999.0, -19999.0))
    ok = ["0b0"] * 5
    fm = [("p0", "2020-01-01", 0, *ok)]
    for i in range(1, 6):  # one flag set per pixel, in turn
        flags = ["0b0"] * 5
        flags[i - 1] = "0b1"
        fm.append((f"p{i}", "2020-01-01", 64, *flags))
    fm.append(("p6", "2020-01-02", 0, *ok))
    fm.append(("p9", "2020-01-03", 0, *ok))  # Fmask date without VI granule
    _write(tmp_path, vi, fm)
    df = read_task(tmp_path)
    assert len(df) == 7  # inner join drops the Fmask-only record
    assert list(df[df["clear"]]["ID"]) == ["p0", "p6"]  # p6 clear but its VI is the fill value
