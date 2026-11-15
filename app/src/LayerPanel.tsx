import { useEffect, useRef, useState } from "react";
import { Explain } from "./Explain";
import { formatTagged } from "./format";
import {
  BACKDROP_OPTIONS,
  type BackdropId,
  COLOUR_METRICS,
  DIVERGING,
  type Domain,
  RAMPS,
  domainOf,
  fieldValues,
  gridDomain,
} from "./mapLayers";
import {
  DELTA_METRICS,
  type OptionDeltaMetric,
  type RegionOptionDeltas,
  deltaDomain,
  deltaLegendSample,
  deltaRampForMetric,
  isDeltaMetric,
} from "./optionDeltas";
import { metricName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import type { FieldColourMetric, RegionLayers, RegionalLayer, Tagged } from "./types";

export type FieldColourChoice = FieldColourMetric | OptionDeltaMetric;

export interface LayerChoice {
  colourBy: FieldColourChoice | null;
  layerId: RegionalLayer["layer_id"] | null;
  year: number | null;
  backdrop?: BackdropId;
}

/** Colour ramp with its end values; the numbers carry the meaning, the colours support them. */
function Legend({ domain, ramp, like }: { domain: Domain; ramp: readonly string[]; like: Omit<Tagged, "value"> }) {
  return (
    <div className="legend">
      <div className="legend-bar-wrap" dir="ltr">
        <span className="legend-ramp" style={{ background: `linear-gradient(to right, ${ramp.join(", ")})` }} aria-hidden="true" />
        <span className="legend-ends">
          <span>{formatTagged({ ...like, value: domain[0] })}</span>
          <span>{formatTagged({ ...like, value: domain[1] })}</span>
        </span>
      </div>
      <span className="legend-none">
        <span className="legend-swatch" aria-hidden="true" /> {t("layers.noValue")}
      </span>
    </div>
  );
}

export function fieldColourDomain(layers: RegionLayers, metric: FieldColourMetric): Domain {
  return domainOf(Object.values(fieldValues(layers, metric)));
}

export function LayerPanel({
  layers,
  choice,
  set,
  optionDeltas = null,
  hasBasemap = false,
}: {
  layers: RegionLayers;
  choice: LayerChoice;
  set: (c: LayerChoice) => void;
  optionDeltas?: RegionOptionDeltas | null;
  hasBasemap?: boolean;
}) {
  const [playing, setPlaying] = useState(false);
  const choiceRef = useRef(choice);
  choiceRef.current = choice;
  const setRef = useRef(set);
  setRef.current = set;

  const metric = choice.colourBy;
  const isDelta = isDeltaMetric(metric);
  const currentSample =
    metric && !isDelta ? Object.values(layers.field_colouring[metric] ?? {})[0] : undefined;
  const deltaSample = metric && isDelta && optionDeltas ? deltaLegendSample(optionDeltas, metric) : undefined;
  const activeSample = currentSample ?? deltaSample;

  const layer = layers.layers.find((l) => l.layer_id === choice.layerId) ?? null;
  const years = layer?.grid.years ?? [];
  const year = choice.year !== null && years.includes(choice.year) ? choice.year : years[years.length - 1];
  const yi = layer ? layer.region_mean.x.findIndex((x) => Number(x) === year) : -1;
  // Text twin of the map colours (T9.7): the lowest and highest cell of the shown year.
  const gi = layer && year !== undefined ? layer.grid.years.indexOf(year) : -1;
  const cellValues = layer && gi >= 0 ? layer.grid.cells.map((c) => c.values[gi]).filter((v): v is number => v != null) : [];
  const cellRange = cellValues.length > 0 ? [Math.min(...cellValues), Math.max(...cellValues)] : null;
  const activeBackdrop: BackdropId = choice.backdrop ?? "modis";

  useEffect(() => {
    if (!layer) setPlaying(false);
  }, [layer]);

  useEffect(() => {
    if (!playing || !layer || years.length < 2) return;
    const timer = window.setInterval(() => {
      const cur = choiceRef.current;
      const curYear = cur.year !== null && years.includes(cur.year) ? cur.year : years[years.length - 1];
      const idx = years.indexOf(curYear);
      const nextYear = years[(idx + 1) % years.length];
      setRef.current({ ...cur, layerId: layer.layer_id, year: nextYear });
    }, 850);
    return () => window.clearInterval(timer);
  }, [playing, layer?.layer_id, years]);

  const stepYear = (delta: number) => {
    if (!layer || years.length === 0 || year === undefined) return;
    setPlaying(false);
    const idx = years.indexOf(year);
    const nextIdx = (idx + delta + years.length) % years.length;
    set({ ...choice, layerId: layer.layer_id, year: years[nextIdx] });
  };

  return (
    <section className="layer-panel" aria-labelledby="layers-h">
      <h2 id="layers-h">{t("layers.heading")}</h2>
      <fieldset>
        <legend>{t("layers.colour")}</legend>
        <label>
          <input type="radio" name="colour-by" checked={metric === null} onChange={() => set({ ...choice, colourBy: null })} />{" "}
          {t("layers.none")}
        </label>

        <p className="layer-group-heading">{t("layers.group.current")}</p>
        {COLOUR_METRICS.filter((m) => layers.field_colouring[m]).map((m) => (
          <label key={m}>
            <input type="radio" name="colour-by" checked={metric === m} onChange={() => set({ ...choice, colourBy: m })} />{" "}
            {metricName(m)}
          </label>
        ))}

        {optionDeltas && (
          <>
            <p className="layer-group-heading">{t("layers.group.deltas")}</p>
            {DELTA_METRICS.filter((m) => optionDeltas.summary[m]?.valid_count > 0).map((m) => (
              <label key={m}>
                <input
                  type="radio"
                  name="colour-by"
                  checked={metric === m}
                  onChange={() => set({ ...choice, colourBy: m })}
                />{" "}
                {metricName(m)}
              </label>
            ))}
          </>
        )}

        {metric && activeSample && (
          <>
            <p className="muted">
              {t(isDelta ? "layers.colour.deltaNote" : "layers.colour.note")}{" "}
              <TagBadge tag={activeSample.tag} source={activeSample.source} />
            </p>
            {isDelta && optionDeltas ? (
              <Legend
                domain={deltaDomain(optionDeltas, metric as OptionDeltaMetric)}
                ramp={deltaRampForMetric(metric as OptionDeltaMetric)}
                like={activeSample}
              />
            ) : (
              <Legend
                domain={fieldColourDomain(layers, metric as FieldColourMetric)}
                ramp={RAMPS.sequential}
                like={activeSample}
              />
            )}
          </>
        )}
      </fieldset>

      <fieldset>
        <legend>{t("layers.regional")}</legend>
        <label>
          <input type="radio" name="regional" checked={!layer} onChange={() => set({ ...choice, layerId: null })} />{" "}
          {t("layers.none")}
        </label>
        {layers.layers.map((l) => (
          <label key={l.layer_id}>
            <input
              type="radio"
              name="regional"
              checked={layer?.layer_id === l.layer_id}
              onChange={() => set({ ...choice, layerId: l.layer_id })}
            />{" "}
            {t(`layer.${l.layer_id}`)}
            {l.layer_id === "smap_anomaly" && <Explain id="soil_moisture_anomaly" />}
          </label>
        ))}
        {layer && year !== undefined && (
          <div className="layer-detail">
            <div className="scrubber-transport" role="group" aria-label={t("layers.year")}>
              <button
                type="button"
                className="scrubber-btn"
                onClick={() => stepYear(-1)}
                aria-label={t("layers.prevYear")}
                title={t("layers.prevYear")}
              >
                ◀
              </button>
              <button
                type="button"
                className="scrubber-btn scrubber-play-btn"
                aria-pressed={playing}
                onClick={() => setPlaying((p) => !p)}
              >
                {t(playing ? "layers.pause" : "layers.play")}
              </button>
              <button
                type="button"
                className="scrubber-btn"
                onClick={() => stepYear(1)}
                aria-label={t("layers.nextYear")}
                title={t("layers.nextYear")}
              >
                ▶
              </button>
            </div>
            <label className="slider">
              <span>{t("layers.year")}</span>
              <input
                type="range"
                min={0}
                max={years.length - 1}
                step={1}
                value={years.indexOf(year)}
                aria-valuetext={String(year)}
                onChange={(e) => {
                  setPlaying(false);
                  set({ ...choice, layerId: layer.layer_id, year: years[Number(e.target.value)] });
                }}
              />
              <output>{year}</output>
            </label>
            <Legend
              domain={gridDomain(layer)}
              ramp={DIVERGING.has(layer.layer_id) ? RAMPS.diverging : RAMPS.sequential}
              like={layer.grid}
            />
            <p>
              {t("layers.mean", { year })}{" "}
              <TaggedValue
                v={{
                  value: yi < 0 ? null : (layer.region_mean.values[yi] ?? null),
                  unit: layer.region_mean.unit,
                  tag: layer.region_mean.tag,
                  source: layer.region_mean.source,
                }}
              />
            </p>
            {cellRange && (
              <p>
                {t("layers.cells", {
                  year,
                  lo: formatTagged({ ...layer.grid, value: cellRange[0] }),
                  hi: formatTagged({ ...layer.grid, value: cellRange[1] }),
                })}{" "}
                <TagBadge tag={layer.grid.tag} source={layer.grid.source} />
              </p>
            )}
            <p>
              {t("ctx.trend")} <TaggedValue v={layer.trend} />
            </p>
            <p className={layer.scale_flag ? "flag flag-coarse" : "flag flag-fine"}>
              <span aria-hidden="true">{layer.scale_flag ? "◌" : "●"}</span>{" "}
              {t(layer.scale_flag ? "ctx.coarse" : "ctx.fine", { km: layer.resolution_km })}
            </p>
            <p className="muted ctx-source">{layer.resolution_source}</p>

            {layers.layers.length > 1 && (
              <div className="sync-snapshot" aria-live="polite">
                <p className="sync-snapshot-head">{t("layers.snapshotHeading", { year })}</p>
                <dl className="sync-snapshot-list">
                  {layers.layers.map((other) => {
                    const oi = other.region_mean.x.findIndex((x) => Number(x) === year);
                    const oval = oi >= 0 ? (other.region_mean.values[oi] ?? null) : null;
                    return (
                      <div
                        key={other.layer_id}
                        className={other.layer_id === layer.layer_id ? "sync-row sync-row--active" : "sync-row"}
                      >
                        <dt>{t(`layer.${other.layer_id}`)}</dt>
                        <dd>
                          {oval != null ? (
                            <TaggedValue
                              v={{
                                value: oval,
                                unit: other.region_mean.unit,
                                tag: other.region_mean.tag,
                                source: other.region_mean.source,
                              }}
                            />
                          ) : (
                            <span className="muted">{t("layers.noYearData", { year })}</span>
                          )}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              </div>
            )}
          </div>
        )}
      </fieldset>

      {hasBasemap && (
        <fieldset className="backdrop-fieldset">
          <legend>{t("layers.backdrop.heading")}</legend>
          {BACKDROP_OPTIONS.map((opt) => (
            <label key={opt.id}>
              <input
                type="radio"
                name="gibs-backdrop"
                checked={activeBackdrop === opt.id}
                onChange={() => set({ ...choice, backdrop: opt.id })}
              />{" "}
              {t(`layers.backdrop.${opt.id}`)}
            </label>
          ))}
          <p className="muted ctx-source">{t("layers.backdrop.note")}</p>
        </fieldset>
      )}

      <div className="scale-contract-card" role="note" aria-label={t("layers.scaleCard.heading")}>
        <h3>{t("layers.scaleCard.heading")}</h3>
        <p className="flag flag-fine">
          <span aria-hidden="true">●</span> {t("layers.scaleCard.fine")}
        </p>
        <p className="flag flag-coarse">
          <span aria-hidden="true">◌</span> {t("layers.scaleCard.coarse")}
        </p>
      </div>
    </section>
  );
}
