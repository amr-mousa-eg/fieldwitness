# Stretching the prediction ranges to match reality: a negative result

*12 Nov 2026. This experiment is on the branch `experiment/conformal` only and is not part of the live website. All numbers come from `results/hindcast/conformal/before_after.md`, which also gives every confidence range.*

## The problem

For each field and season, FieldWitness gives a middle prediction and a range it calls "90 %". If those ranges were honest, the real satellite value would fall inside them about 9 times in 10.

In the 2022–2024 test (forecast run, total season greenness) they were far too narrow:

| Crop | Seasons | Inside the "90 %" range |
|---|---|---|
| Maize | 124 | 27 % |
| Sorghum | 142 | 44 % |
| Winter wheat | 197 | 24 % |

## What we did

We measured how far off the model was in earlier seasons. We ran the same forecast pipeline as if it were the end of 2018, 2019 and 2020, then compared it with the 2019, 2020 and 2021 satellite data. That gave 127 maize, 134 sorghum and 167 winter wheat past seasons.

From those past misses we worked out one stretch factor per crop, which is a standard method called "conformal" calibration. The factor makes the range wide enough to have covered 90 % of the past misses. The middle prediction was not touched.

The factor is about 3.5 for maize, 2.0 for sorghum and 3.4 for winter wheat. We then applied it, unchanged, to 2022–2024, which the method never saw. For the primary result, a field's own 10 km block was left out when its stretch factor was worked out.

## What happened

The ranges now cover much more, but not 90 %:

| Crop | Coverage after | Range width |
|---|---|---|
| Maize | 80 % | 3.5 times wider |
| Sorghum | 69 % | 2.0 times wider |
| Winter wheat | 76 % | 3.4 times wider |

None of the three crops reaches the agreed target of 85–95 %, so **the test failed for every crop**.

The stretch did make the ranges more useful overall. The interval score, which penalises both a too-wide range and a miss, improved by more than half. For example, maize went from 272 to 117 (lower is better).

On the past seasons the factors worked: 90 % coverage in cross-checking. The test years simply missed more widely than the past years did. Coverage was lowest in 2022 for maize (67 %) and sorghum (59 %), and in 2023 for winter wheat (64 %). A stretch learned from the past cannot promise coverage when the future behaves differently.

## What it cannot fix

For maize and winter wheat the middle prediction itself is off. Most real values fall below the middle prediction: only 31 % of maize and 31 % of wheat values are above it, when it should be half. **Widening the range cannot fix a biased centre.**

For winter wheat the timing of the green peak is also off: it is predicted 36 days late for the median season. That is the same problem the separate heat-clock experiment looks at.

## Recommendation

**Do not adopt.** It failed the pre-registered test for all three crops. The current ranges stay as they are, and nothing on the website changes.

Adopting a fixed version later would need:

1. New interval fields in the field packs, and a rebuild of all packs.
2. A change wherever the browser code shows or replays the ranges (the Field Card and the 3D view).
3. New Methods text.
4. A new parity test between the Python and browser numbers.
5. A new pre-registered test on seasons that played no part in the decision (2025 or later).
