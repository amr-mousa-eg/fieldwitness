import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CropChips } from "./CropChips";
import { Explain } from "./Explain";
import { loadSeries } from "./data";
import { formatDate, harvestDayToDate } from "./format";
import { cropName, t } from "./strings";
import { TagBadge, TaggedValue } from "./tags";
import type { FieldPack, FieldSeries, Season, Tagged, TaggedSeries } from "./types";

const DAY = 86_400_000;
const CHART = { ndvi: "#3e7d3a", evi: "#6b5ea8", smooth: "#22313a", marks: "#8a6a1f" };

interface Point {
  x: number;
  y: number;
}

function points(s: TaggedSeries): Point[] {
  return (s.x as string[]).flatMap((d, i) => {
    const y = s.values[i];
    return y === null ? [] : [{ x: Date.parse(`${d}T00:00:00Z`), y }];
  });
}

/** Calendar time of a season mark; null when the season has no value (e.g. fallow). */
function markTime(season: Season, mark: Tagged): number | null {
  return mark.value === null ? null : harvestDayToDate(season.year, mark.value).getTime();
}

function SeasonDate({ season, mark }: { season: Season; mark: Tagged }) {
  const time = markTime(season, mark);
  if (time === null) return <span className="muted">{t("value.none")}</span>;
  return <TaggedValue v={mark} text={formatDate(new Date(time))} />;
}

function cropSource(s: Season): string {
  return t(`story.crop.${s.crop_source}` as "story.crop.label");
}

function Timeline({ story }: { story: Season[] }) {
  const seasons = [...story].sort((a, b) => a.year - b.year || a.index - b.index);
  return (
    <section aria-labelledby="timeline-h">
      <h3 id="timeline-h">{t("story.timeline")}</h3>
      <p className="muted">{t("story.timeline.note")}</p>
      <ol className="timeline">
        {seasons.map((s) => (
          <li key={`${s.year}-${s.index}`} className="season">
            <h4>
              {s.year}
              {s.index > 0 ? ` (${s.index + 1})` : ""}
            </h4>
            {s.crop ? <CropChips sequence={[s.crop]} /> : <span>{t("story.crop.none")}</span>}
            <p className="season-conf">
              {t("story.crop.conf", { conf: Math.round(s.crop_conf * 100), source: cropSource(s) })}
            </p>
            <dl>
              <dt>{t("story.sowing")}</dt>
              <dd>
                <SeasonDate season={s} mark={s.sos} />
              </dd>
              <dt>{t("story.peak")}</dt>
              <dd>
                <SeasonDate season={s} mark={s.peak} />
              </dd>
              <dt>{t("story.harvest")}</dt>
              <dd>
                <SeasonDate season={s} mark={s.eos} />
              </dd>
              <dt>{t("story.cover")}</dt>
              <dd>
                <TaggedValue v={s.cover_days} />
              </dd>
              <dt>{t("story.bare")}</dt>
              <dd>
                <TaggedValue v={s.bare_days} />
              </dd>
            </dl>
            <p className="muted season-clear">{t("story.clear", { n: s.clear_obs })}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function GreennessChart({ pack, series }: { pack: FieldPack; series: FieldSeries }) {
  const [focus, setFocus] = useState<string>("all");
  const [showEvi, setShowEvi] = useState(false);
  const ndvi = useMemo(() => points(series.ndvi), [series]);
  const evi = useMemo(() => points(series.evi), [series]);
  const smooth = useMemo(() => points(series.ndvi_smooth), [series]);
  const seasons = pack.story.filter((s) => s.sos.value !== null && s.eos.value !== null);

  const domain = useMemo((): [number, number] => {
    const s = pack.story.find((x) => `${x.year}-${x.index}` === focus);
    const sos = s && markTime(s, s.sos);
    const eos = s && markTime(s, s.eos);
    if (sos && eos) return [sos - 60 * DAY, eos + 60 * DAY];
    return [smooth[0]?.x ?? 0, smooth[smooth.length - 1]?.x ?? 1];
  }, [focus, pack.story, smooth]);
  const inView = (p: Point) => p.x >= domain[0] && p.x <= domain[1];
  const nearestSmooth = (time: number) =>
    smooth.reduce((best, p) => (Math.abs(p.x - time) < Math.abs(best.x - time) ? p : best), smooth[0]);
  const yearTicks = useMemo(() => {
    const ticks: number[] = [];
    for (let y = new Date(domain[0]).getUTCFullYear(); y <= new Date(domain[1]).getUTCFullYear() + 1; y++) {
      const time = Date.UTC(y, 0, 1);
      if (time >= domain[0] && time <= domain[1]) ticks.push(time);
    }
    return ticks;
  }, [domain]);
  const span = domain[1] - domain[0];
  const tickFmt = (time: number) =>
    new Date(time).toLocaleDateString("en-GB", span > 800 * DAY ? { year: "numeric", timeZone: "UTC" } : { month: "short", year: "numeric", timeZone: "UTC" });

  return (
    <section aria-labelledby="chart-h">
      <h3 id="chart-h">
        {t("story.chart")}
        <Explain id="ndvi" />
      </h3>
      <p className="muted">{t("story.chart.note")}</p>
      <div className="chart-controls">
        <label>
          {t("story.chart.show")}{" "}
          <select value={focus} onChange={(e) => setFocus(e.target.value)}>
            <option value="all">{t("story.chart.all")}</option>
            {seasons.map((s) => (
              <option key={`${s.year}-${s.index}`} value={`${s.year}-${s.index}`}>
                {t("story.chart.season", { year: s.year, crop: s.crop ? cropName(s.crop) : "" })}
              </option>
            ))}
          </select>
        </label>
        <label>
          <input type="checkbox" checked={showEvi} onChange={(e) => setShowEvi(e.target.checked)} />{" "}
          {t("story.chart.evi")}
        </label>
      </div>
      <ul className="chart-key">
        <li>
          <span className="key-dot" style={{ background: CHART.ndvi }} /> {t("story.series.ndvi")}{" "}
          <TagBadge tag={series.ndvi.tag} source={series.ndvi.source} />
        </li>
        {showEvi && (
          <li>
            <span className="key-triangle" style={{ borderBottomColor: CHART.evi }} /> {t("story.series.evi")}{" "}
            <TagBadge tag={series.evi.tag} source={series.evi.source} />
          </li>
        )}
        <li>
          <span className="key-line" style={{ background: CHART.smooth }} /> {t("story.series.smooth")}{" "}
          <TagBadge tag={series.ndvi_smooth.tag} source={series.ndvi_smooth.source} />
        </li>
      </ul>
      <div className="chart" role="img" aria-label={t("story.chart.note")}>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="2 4" vertical={false} />
            <XAxis
              dataKey="x"
              type="number"
              scale="time"
              domain={domain}
              allowDataOverflow
              ticks={yearTicks.length > 1 ? yearTicks : undefined}
              tickFormatter={tickFmt}
            />
            <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} width={40} />
            <Tooltip
              labelFormatter={(time) => formatDate(new Date(Number(time)))}
              formatter={(v) => Number(v).toFixed(2)}
            />
            {seasons.map((s) => {
              const sos = markTime(s, s.sos)!;
              const eos = markTime(s, s.eos)!;
              return [
                <ReferenceLine key={`sos-${s.year}`} x={sos} stroke={CHART.marks} strokeDasharray="3 3" ifOverflow="hidden" />,
                <ReferenceLine key={`eos-${s.year}`} x={eos} stroke={CHART.marks} strokeDasharray="3 3" ifOverflow="hidden" />,
              ];
            })}
            <Line
              data={smooth.filter(inView)}
              dataKey="y"
              name={t("story.series.smooth")}
              stroke={CHART.smooth}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Scatter data={ndvi.filter(inView)} dataKey="y" name={t("story.series.ndvi")} fill={CHART.ndvi} isAnimationActive={false} />
            {showEvi && (
              <Scatter
                data={evi.filter(inView)}
                dataKey="y"
                name={t("story.series.evi")}
                fill={CHART.evi}
                shape="triangle"
                isAnimationActive={false}
              />
            )}
            {seasons.map((s) => {
              const peak = markTime(s, s.peak);
              if (peak === null || smooth.length === 0) return null;
              return (
                <ReferenceDot
                  key={`peak-${s.year}`}
                  x={peak}
                  y={nearestSmooth(peak).y}
                  r={6}
                  fill="none"
                  stroke={CHART.marks}
                  strokeWidth={2}
                  ifOverflow="hidden"
                />
              );
            })}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function FieldStory({ pack, regionId }: { pack: FieldPack; regionId: string }) {
  const [series, setSeries] = useState<FieldSeries | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setSeries(null);
    setError(null);
    loadSeries(regionId, pack.field.field_id)
      .then(setSeries)
      .catch((e: Error) => setError(e.message));
  }, [regionId, pack.field.field_id]);

  return (
    <div className="story">
      {series && <GreennessChart pack={pack} series={series} />}
      {error && <p className="muted">{t("story.series.missing")}</p>}
      <Timeline story={pack.story} />
    </div>
  );
}
