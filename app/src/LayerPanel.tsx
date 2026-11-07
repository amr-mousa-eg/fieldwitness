import { Explain } from "./Explain";
import { formatTagged } from "./format";
import { COLOUR_METRICS, DIVERGING, type Domain, RAMPS, domainOf, fieldValues, gridDomain } from "./mapLayers";
import { metricName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import type { FieldColourMetric, RegionLayers, RegionalLayer, Tagged } from "./types";

export interface LayerChoice {
  colourBy: FieldColourMetric | null;
  layerId: RegionalLayer["layer_id"] | null;
  year: number | null;
}

/** Colour ramp with its end values; the numbers carry the meaning, the colours support them. */
function Legend({ domain, ramp, like }: { domain: Domain; ramp: readonly string[]; like: Omit<Tagged, "value"> }) {
  return (
    <div className="legend">
      <span className="legend-ramp" style={{ background: `linear-gradient(to right, ${ramp.join(", ")})` }} aria-hidden="true" />
      <span className="legend-ends">
        <span>{formatTagged({ ...like, value: domain[0] })}</span>
        <span>{formatTagged({ ...like, value: domain[1] })}</span>
      </span>
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
}: {
  layers: RegionLayers;
  choice: LayerChoice;
  set: (c: LayerChoice) => void;
}) {
  const metric = choice.colourBy;
  const sample = metric ? Object.values(layers.field_colouring[metric] ?? {})[0] : undefined;
  const layer = layers.layers.find((l) => l.layer_id === choice.layerId) ?? null;
  const years = layer?.grid.years ?? [];
  const year = choice.year !== null && years.includes(choice.year) ? choice.year : years[years.length - 1];
  const yi = layer ? layer.region_mean.x.findIndex((x) => Number(x) === year) : -1;
  // Text twin of the map colours (T9.7): the lowest and highest cell of the shown year.
  const gi = layer && year !== undefined ? layer.grid.years.indexOf(year) : -1;
  const cellValues = layer && gi >= 0 ? layer.grid.cells.map((c) => c.values[gi]).filter((v): v is number => v != null) : [];
  const cellRange = cellValues.length > 0 ? [Math.min(...cellValues), Math.max(...cellValues)] : null;

  return (
    <section className="layer-panel" aria-labelledby="layers-h">
      <h2 id="layers-h">{t("layers.heading")}</h2>
      <fieldset>
        <legend>{t("layers.colour")}</legend>
        <label>
          <input type="radio" name="colour-by" checked={metric === null} onChange={() => set({ ...choice, colourBy: null })} />{" "}
          {t("layers.none")}
        </label>
        {COLOUR_METRICS.filter((m) => layers.field_colouring[m]).map((m) => (
          <label key={m}>
            <input type="radio" name="colour-by" checked={metric === m} onChange={() => set({ ...choice, colourBy: m })} />{" "}
            {metricName(m)}
          </label>
        ))}
        {metric && sample && (
          <>
            <p className="muted">
              {t("layers.colour.note")} <TagBadge tag={sample.tag} source={sample.source} />
            </p>
            <Legend domain={fieldColourDomain(layers, metric)} ramp={RAMPS.sequential} like={sample} />
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
            <label className="slider">
              <span>{t("layers.year")}</span>
              <input
                type="range"
                min={0}
                max={years.length - 1}
                step={1}
                value={years.indexOf(year)}
                aria-valuetext={String(year)}
                onChange={(e) => set({ ...choice, layerId: layer.layer_id, year: years[Number(e.target.value)] })}
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
          </div>
        )}
      </fieldset>
    </section>
  );
}
