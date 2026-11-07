import { t } from "./strings";

/** CLAUDE.md rule 5: coarse sources are context only. True = pixel larger than field area / 4. */
export function ScaleFlags({ flags }: { flags: Record<string, boolean> }) {
  const entries = Object.entries(flags).sort(([a, x], [b, y]) => Number(x) - Number(y) || a.localeCompare(b));
  return (
    <section className="scale-flags" aria-labelledby="scale-h">
      <h3 id="scale-h">{t("scale.heading")}</h3>
      <ul>
        {entries.map(([source, coarse]) => (
          <li key={source} className={coarse ? "flag flag-coarse" : "flag flag-fine"}>
            <span aria-hidden="true">{coarse ? "◌" : "●"}</span>{" "}
            {t(coarse ? "scale.coarse" : "scale.fine", { source })}
          </li>
        ))}
      </ul>
      <p className="muted">{t("scale.note")}</p>
    </section>
  );
}
