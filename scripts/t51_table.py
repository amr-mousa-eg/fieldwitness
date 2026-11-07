"""T5.1: build data/neighbours/ks_t14slh_field_season.parquet and contrast counts."""

from fieldwitness.neighbours import table

df = table.build()
s = table.write(df)
print({k: s[k] for k in ("rows", "rows_with_outcome", "fields")})
for r in s["contrast_counts"]:
    print(r)
