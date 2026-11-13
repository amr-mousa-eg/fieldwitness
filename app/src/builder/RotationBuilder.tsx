// Rotation Builder (feature flag `?builder=1`): place crops in three season slots, then "Grow"
// plays the rotation in the Field in 3D scene. The 3D replay is simulated in the browser
// (field3d/physics.ts, parity-tested against Python); every number in the result panel comes from
// the field pack (the ranking's metrics), never from the replay. Missing numbers read
// "not simulated". No points, scores, yield or profit wording: feedback is relative to Current.
import { useEffect, useMemo, useRef, useState } from "react";
import "./RotationBuilder.css";
import { loadSim3DInputs } from "../data";
import { simulateOption } from "../field3d/physics";
import { compareToCurrent, computeBareSoilMonths, type SummaryToken } from "../fieldSummary";
import { cropName, getLocale, t } from "../strings";
import { type BuilderKey, bt } from "./strings";
import { TagBadge } from "../tags";
import { emitTour } from "../tourEvents";
import type { FieldPack, FieldSim3DInputs, Option, Sim3DOption, Tagged } from "../types";
import { N_SEASONS, type Placed, type RuleContext, cardState, isComplete, legalSequences, optionFor } from "./rules";

const CARD_ORDER = ["maize", "sorghum", "winter_wheat", "cover_crop", "fallow"];
const DRAG_PX = 8;

function Tokens({ tokens }: { tokens: SummaryToken[] }) {
  const isAr = getLocale() === "ar";
  return (
    <>
      {tokens.map((k, i) =>
        k.kind === "text" ? (
          <span key={i}>{k.text}</span>
        ) : k.kind === "grade" ? (
          <strong key={i}>{isAr ? t("score.gradeLabel", { grade: k.grade }) : `grade ${k.grade}`}</strong>
        ) : (
          <span key={i} className="tagged">
            {k.value} {k.unit} <TagBadge tag={k.tag} source={k.source} />
          </span>
        ),
      )}
    </>
  );
}

function Cell({ m, unit, digits = 0, months = false }: { m: Tagged | undefined; unit: string; digits?: number; months?: boolean }) {
  if (!m || m.value === null || m.value === undefined) return <td className="muted">{t("season.notSimulated")}</td>;
  const v = months ? computeBareSoilMonths(m.value) : m.value;
  return (
    <td>
      {v.toFixed(digits)} {unit} <TagBadge tag={m.tag} source={m.source} />
    </td>
  );
}

function ResultRow({ label, option }: { label: string; option: Option | null }) {
  const m = option?.metrics ?? {};
  const mm = t("unit.mm");
  return (
    <tr>
      <th scope="row">{label}</th>
      <Cell m={m.water_use_mm} unit={mm} />
      <Cell m={m.bad_year_water_mm} unit={mm} />
      <Cell m={m.cover_days} unit={bt("builder.months")} digits={1} months />
      <td>{option?.grade ?? t("season.notSimulated")}</td>
    </tr>
  );
}

export default function RotationBuilder({
  pack,
  regionId,
  onGrow,
  onClear,
}: {
  pack: FieldPack;
  regionId: string;
  onGrow: (o: Sim3DOption) => void;
  onClear: () => void;
}) {
  const [inp, setInp] = useState<FieldSim3DInputs | null>(null);
  const [error, setError] = useState(false);
  const [placed, setPlaced] = useState<Placed>(Array(N_SEASONS).fill(null));
  const [slot, setSlot] = useState(0);
  const [grown, setGrown] = useState<string[] | null>(null);
  const [drag, setDrag] = useState<{ crop: string; x: number; y: number } | null>(null);
  const dragStart = useRef<{ crop: string; x: number; y: number; moved: boolean } | null>(null);
  const suppressClick = useRef(false);

  useEffect(() => {
    let live = true;
    loadSim3DInputs(regionId, pack.field.field_id)
      .then((d) => live && setInp(d))
      .catch(() => live && setError(true));
    return () => {
      live = false;
    };
  }, [regionId, pack.field.field_id]);

  const ctx: RuleContext | null = useMemo(() => {
    if (!inp) return null;
    const families = Object.fromEntries(Object.entries(inp.slots.crops).map(([k, s]) => [k, s.family]));
    return { legal: legalSequences(pack), families, maxFamilyRun: inp.slots.max_family_run };
  }, [inp, pack]);

  const cards = useMemo(
    () => (ctx && inp ? CARD_ORDER.filter((c) => c in inp.slots.crops && ctx.legal.some((s) => s.includes(c))) : []),
    [ctx, inp],
  );

  if (error) return <p className="muted">{bt("builder.missing")}</p>;
  if (!inp || !ctx) return <p className="muted">{bt("builder.loading")}</p>;

  const place = (crop: string, at: number) => {
    if (!cardState(placed, at, crop, ctx).ok) return;
    const next = placed.map((c, i) => (i === at ? crop : c));
    setPlaced(next);
    emitTour("builder-place");
    setGrown(null);
    const empty = next.findIndex((c) => c === null);
    setSlot(empty >= 0 ? empty : at);
  };
  const clearSlot = (at: number) => {
    setPlaced(placed.map((c, i) => (i === at ? null : c)));
    setSlot(at);
    setGrown(null);
    onClear();
  };

  // Pointer drag (mouse and touch): a card dropped on a slot is placed there.
  const onPointerDown = (crop: string) => (e: React.PointerEvent) => {
    dragStart.current = { crop, x: e.clientX, y: e.clientY, moved: false };
    const move = (ev: PointerEvent) => {
      const s = dragStart.current;
      if (!s) return;
      if (!s.moved && Math.hypot(ev.clientX - s.x, ev.clientY - s.y) > DRAG_PX) s.moved = true;
      if (s.moved) setDrag({ crop: s.crop, x: ev.clientX, y: ev.clientY });
    };
    const up = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      const s = dragStart.current;
      dragStart.current = null;
      setDrag(null);
      if (!s?.moved) return;
      suppressClick.current = true;
      const target = document.elementFromPoint(ev.clientX, ev.clientY)?.closest("[data-builder-slot]");
      if (target) place(s.crop, Number(target.getAttribute("data-builder-slot")));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const complete = isComplete(placed, ctx);
  const grow = () => {
    if (!complete) return;
    const seq = placed as string[];
    const label = bt("builder.yours", { seq: seq.map((c) => cropName(c)).join(" → ") });
    const ranked = optionFor(pack, seq);
    onGrow(simulateOption(inp, seq, ["normal", "dry", "hot"], { option_id: "builder", label, rank: ranked?.rank ?? -1 }));
    setGrown(seq);
    emitTour("builder-grow");
  };

  const current = pack.options.find((o) => o.option_id === "current") ?? null;
  const top = pack.options.filter((o) => o.option_id !== "current").sort((a, b) => a.rank - b.rank)[0] ?? null;
  const yours = grown ? optionFor(pack, grown) : null;
  const currentHasMetrics = !!current?.metrics.water_use_mm && !!current?.metrics.cover_days;
  const isCurrent = !!grown && !!current && grown.join("|") === current.sequence.join("|");

  return (
    <section className="builder" aria-labelledby="builder-h">
      <h3 id="builder-h">{bt("builder.title")}</h3>
      <p className="muted">{bt("builder.intro")}</p>

      <ol className="builder-slots" aria-label={bt("builder.slots")}>
        {placed.map((c, i) => (
          <li key={i} className="builder-slot-wrap">
            <button
              type="button"
              className={`builder-slot${slot === i ? " selected" : ""}${c ? " filled" : ""}`}
              data-builder-slot={i}
              aria-pressed={slot === i}
              aria-label={bt("builder.slotLabel", { n: i + 1, crop: c ? cropName(c) : bt("builder.empty") })}
              onClick={() => setSlot(i)}
            >
              <span className="builder-slot-n">{bt("builder.season", { n: i + 1 })}</span>
              <span className="builder-slot-crop">{c ? cropName(c) : bt("builder.empty")}</span>
            </button>
            {c && (
              <button type="button" className="builder-clear" onClick={() => clearSlot(i)} aria-label={bt("builder.clear", { n: i + 1 })}>
                ×
              </button>
            )}
          </li>
        ))}
      </ol>

      <p className="builder-hint muted">{bt("builder.hint", { n: slot + 1 })}</p>
      <ul className="builder-cards" aria-label={bt("builder.cards")}>
        {cards.map((c) => {
          const st = cardState(placed, slot, c, ctx);
          const reason = st.ok
            ? null
            : bt(`builder.reason.${st.rule}` as BuilderKey, { n: ctx.maxFamilyRun, family: st.family ?? "" });
          return (
            <li key={c}>
              <button
                type="button"
                className={`builder-card crop-${c}`}
                aria-disabled={!st.ok}
                aria-describedby={reason ? `builder-why-${c}` : undefined}
                onPointerDown={st.ok ? onPointerDown(c) : undefined}
                onClick={() => {
                  if (suppressClick.current) {
                    suppressClick.current = false;
                    return;
                  }
                  place(c, slot);
                }}
              >
                <span className="builder-card-name">{cropName(c)}</span>
                {reason && (
                  <span id={`builder-why-${c}`} className="builder-why">
                    {reason}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="builder-actions">
        <button type="button" className="builder-grow" onClick={grow} disabled={!complete}>
          {bt("builder.grow")}
        </button>
        <span className="muted" role="status">
          {complete ? bt("builder.ready") : bt("builder.notReady")}
        </span>
      </div>

      {grown && (
        <div className="builder-result" aria-live="polite">
          <p className="builder-sentence">
            {isCurrent ? (
              bt("builder.isCurrent")
            ) : yours && current && currentHasMetrics ? (
              <Tokens tokens={compareToCurrent(current, { ...yours, option_id: grown.join("|") }).tokens} />
            ) : (
              bt("builder.noCurrent")
            )}
          </p>
          <div className="table-wrap">
            <table className="builder-table">
              <thead>
                <tr>
                  <th scope="col">{bt("builder.col.rotation")}</th>
                  <th scope="col">{bt("builder.col.water")}</th>
                  <th scope="col">{bt("builder.col.badYear")}</th>
                  <th scope="col">{bt("builder.col.bare")}</th>
                  <th scope="col">{bt("builder.col.grade")}</th>
                </tr>
              </thead>
              <tbody>
                <ResultRow label={bt("builder.row.yours", { seq: grown.map((c) => cropName(c)).join(" → ") })} option={yours} />
                <ResultRow label={bt("builder.row.current", { seq: current ? current.sequence.map((c) => cropName(c)).join(" → ") : "" })} option={current} />
                <ResultRow label={bt("builder.row.top", { seq: top ? top.sequence.map((c) => cropName(c)).join(" → ") : "" })} option={top} />
              </tbody>
            </table>
          </div>
          <p className="muted">{bt("builder.provenance")}</p>
        </div>
      )}

      {drag && (
        <div className="builder-ghost" style={{ left: drag.x, top: drag.y }} aria-hidden="true">
          {cropName(drag.crop)}
        </div>
      )}
    </section>
  );
}
