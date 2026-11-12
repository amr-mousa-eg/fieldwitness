# Can past mistakes tell us which predictions to trust? A negative result

*12 Nov 2026. This experiment is on the branch `experiment/reliability-grades` only and is not part of the live website. All numbers come from `results/hindcast/reliability/test_by_tier.md`.*

## The problem

FieldWitness gives each recommendation an evidence grade (B, C or D), based on whether its "witnesses" agree. When we checked the grades against what really happened in 2022–2024, a better grade did not mean a more accurate prediction:

| Grade | Average error |
|---|---|
| B | 17.0 |
| C | 17.3 |
| D | 24.0 |

The ranges overlap too much to tell the grades apart.

## What we tried

Instead of witness agreement, we tried to learn reliability from measured mistakes. We used the model's own forecasts for 2019, 2020 and 2021, each made with only the data available before that season: 428 field-seasons in all.

We then asked which of five simple rules best predicts how big a field's error will be. The facts allowed were all known before the season:
- how much satellite history the field has;
- how well the model matched that history (its credibility);
- how unsure the forecast itself is;
- the crop;
- the field size.

The rule was picked by testing on held-out 10 km blocks, still inside 2019–2021. Its "reliability tiers" (R1 = most reliable to R4 = least) were then frozen and checked once against 2022–2024.

## What happened

The best rule was simply **"which crop is it"**. Sorghum was predicted best, then maize, then winter wheat, and that order held in 2022–2024:

| Tier (crop) | Average error | Range |
|---|---|---|
| R1 (sorghum) | 12.4 | 10.1–14.7 |
| R2 (maize) | 17.7 | 15.1–20.3 |
| R3 (winter wheat) | 21.1 | 18.7–23.6 |

But the pre-agreed test needed four ordered tiers, and with only three crops the fourth tier stayed empty. It also needed the full model, with all the facts, to rank fields better than crop alone, and it did not.

Within a single crop, nothing we tried could tell which fields would be predicted well. The order also flipped in 2024, when wheat did better than maize. **Result: not shown.**

## What it cannot do

- It cannot say which *field* will be predicted well, only which *crop* tends to be. That is something a farmer can already read off the scoreboard.
- It cannot promise an error size. Errors in 2022–2024 were about 50 % larger than in 2019–2021 overall: 38 % larger for maize, 40 % for winter wheat, and 91 % for sorghum.
- These tiers are not evidence grades and say nothing about the neighbour witness.

## Recommendation

**Do not adopt.** The current grades stay as they are, with their existing "not shown" label.

A future version would need:
1. A new pre-registration and an untouched test season (2025 or later).
2. Pack fields for the tier.
3. Changes to the Field Card and the Methods text.
4. A change to `config/grading.yaml`.
5. New tests.

None of these were changed here.
