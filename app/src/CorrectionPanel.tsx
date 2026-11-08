import { useMemo, useState } from "react";
import { CropChips } from "./CropChips";
import {
  type Corrections,
  type CurrentRotation,
  FALLOW,
  SOURCE_FARMER,
  applyCorrections,
  emptyCorrections,
} from "./corrections";
import { clearCorrections, loadCorrections, saveCorrections } from "./correctionStore";
import { cropName, t } from "./strings";
import { TagBadge } from "./tags";
import type { FieldPack } from "./types";

/** Current rotation of a pack: the Current option's crops on the last seasons of the story. */
export function currentFromPack(pack: FieldPack): CurrentRotation | null {
  const cur = pack.options.find((o) => o.option_id === "current");
  if (!cur || cur.sequence.length === 0 || pack.story.length < cur.sequence.length) return null;
  const years = pack.story.slice(-cur.sequence.length).map((s) => s.year);
  const allowed = new Set(pack.options.flatMap((o) => o.sequence));
  return {
    fieldId: pack.field.field_id,
    years,
    sequence: cur.sequence,
    confidence: 1,
    tag: "D",
    simulatable: cur.sequence.every((c) => allowed.has(c) || c === FALLOW),
    gaps: [],
    secondCrops: {},
  };
}

export function CorrectionPanel({ pack }: { pack: FieldPack }) {
  const fid = pack.field.field_id;
  const cur = useMemo(() => currentFromPack(pack), [pack]);
  const allowed = useMemo(() => new Set(pack.options.flatMap((o) => o.sequence)), [pack.options]);
  const [corr, setCorr] = useState<Corrections>(() => loadCorrections(fid));
  const [saved, setSaved] = useState(true);
  if (!cur) return null;

  const update = (next: Corrections) => {
    setCorr(next);
    setSaved(saveCorrections(fid, next));
  };
  const crops = [...allowed, FALLOW].sort();
  const result = applyCorrections(cur, corr, allowed);
  const hasAny =
    Object.keys(corr.cropByYear).length > 0 || Object.keys(corr.sowingDay).length > 0 || corr.irrigated !== null;

  return (
    <fieldset className="panel">
      <legend>{t("corr.heading")}</legend>
      <p className="muted">{t("corr.intro")}</p>
      {!saved && <p className="notice">{t("corr.nostorage")}</p>}
      {cur.years.map((y, i) => (
        <div key={y}>
          <label>
            {t("corr.crop", { year: y })}
            <select
              value={corr.cropByYear[y] ?? ""}
              onChange={(e) => {
                const c = { ...corr.cropByYear };
                if (e.target.value) c[y] = e.target.value;
                else delete c[y];
                update({ ...corr, cropByYear: c });
              }}
            >
              <option value="">{t("corr.keep")}</option>
              {crops.map((c) => (
                <option key={c} value={c}>
                  {cropName(c)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("corr.sowing", { year: y })}
            <input
              type="number"
              min={1}
              max={366}
              value={corr.sowingDay[y] ?? ""}
              onChange={(e) => {
                const d = { ...corr.sowingDay };
                const n = Number(e.target.value);
                if (e.target.value !== "" && Number.isInteger(n) && n >= 1 && n <= 366) d[y] = n;
                else delete d[y];
                update({ ...corr, sowingDay: d });
              }}
            />
          </label>
          <span className="sr-only">{cur.sequence[i]}</span>
        </div>
      ))}
      <label>
        {t("corr.irrigated")}
        <select
          value={corr.irrigated === null ? "" : corr.irrigated ? "yes" : "no"}
          onChange={(e) => update({ ...corr, irrigated: e.target.value === "" ? null : e.target.value === "yes" })}
        >
          <option value="">{t("corr.irrigated.keep")}</option>
          <option value="yes">{t("corr.irrigated.yes")}</option>
          <option value="no">{t("corr.irrigated.no")}</option>
        </select>
      </label>
      <table className="options">
        <caption>{t("corr.compare")}</caption>
        <thead>
          <tr>
            <th scope="col">{t("corr.year")}</th>
            <th scope="col">{t("corr.satellite")}</th>
            <th scope="col">{t("corr.farmer")}</th>
          </tr>
        </thead>
        <tbody>
          {cur.years.map((y, i) => (
            <tr key={y}>
              <th scope="row">{y}</th>
              <td>
                <CropChips sequence={[cur.sequence[i]]} /> <TagBadge tag="D" />
              </td>
              <td>
                <CropChips sequence={[result.corrected.sequence[i]]} />{" "}
                <TagBadge tag={result.sourceByYear[y] === SOURCE_FARMER ? "E" : "D"} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {result.needsRerun && (
        <p className="notice" role="status">
          {t("corr.rerun")}
        </p>
      )}
      {hasAny && (
        <>
          <ul className="muted">
            {result.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => {
              clearCorrections(fid);
              setCorr(emptyCorrections());
            }}
          >
            {t("corr.reset")}
          </button>
        </>
      )}
    </fieldset>
  );
}
