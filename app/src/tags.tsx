import { Explain } from "./Explain";
import { formatTagged } from "./format";
import { t } from "./strings";
import type { Tag, Tagged } from "./types";

const TAG_KEY = { O: "tag.O", D: "tag.D", E: "tag.E", A: "tag.A" } as const;

/** The one-letter source tag every user-facing number carries (CLAUDE.md rule 3). */
export function TagBadge({ tag, source }: { tag: Tag; source?: string }) {
  const meaning = t(TAG_KEY[tag]);
  return (
    <abbr className={`tag tag-${tag}`} title={source ? `${meaning}. Source: ${source}` : meaning}>
      {tag}
    </abbr>
  );
}

/** A tagged number: value, unit, tag; the 90 % range when the pack has one. */
export function TaggedValue({ v, digits, text }: { v: Tagged; digits?: number; text?: string }) {
  const range =
    v.lo90 != null && v.hi90 != null
      ? t("value.range90", {
          lo: formatTagged({ ...v, value: v.lo90 }, digits),
          hi: formatTagged({ ...v, value: v.hi90 }, digits),
        })
      : null;
  return (
    <span className="tagged" title={range ?? undefined}>
      {text ?? formatTagged(v, digits)} <TagBadge tag={v.tag} source={v.source} />
    </span>
  );
}

export function TagLegend() {
  return (
    <section className="tag-legend" aria-labelledby="tag-legend-h">
      <h3 id="tag-legend-h">
        {t("tag.legend")}
        <Explain id="source_tags" />
      </h3>
      <ul>
        {(["O", "D", "E", "A"] as const).map((tag) => (
          <li key={tag}>
            <TagBadge tag={tag} /> {t(TAG_KEY[tag])}
          </li>
        ))}
      </ul>
    </section>
  );
}
