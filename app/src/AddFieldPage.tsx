import { useEffect, useMemo, useRef, useState } from "react";
import {
  type CustomFieldFormData,
  findNearestAnalysedField,
  generateCsvTemplate,
  getDefaultFormData,
  getRecentHarvestYears,
  isInsideKansasTile,
  KANSAS_CROPS,
  parseCsvInput,
  PRESET_LOCATIONS,
  SOWING_WINDOWS,
} from "./customField";
import { Explain } from "./Explain";
import { setActiveLiveClimateProfile } from "./chatbotContext";
import { fetchLiveClimateProfile, type LiveClimateProfile } from "./liveClimateApi";
import {
  clearAllCustomFields,
  convertFormToRecord,
  type CustomFieldRecord,
  deleteCustomField,
  exportFieldsAsJson,
  importFieldsFromJson,
  loadSavedFields,
  saveCustomField,
} from "./customFieldStore";
import { DEFAULT_PRIORITIES, isDefault, type PriorityKey, PRIORITY_KEYS } from "./rank";
import { routeHref } from "./route";
import { type StringKey, cropName, t } from "./strings";
import { emitTour } from "./tourEvents";
import type { RegionIndex } from "./types";

interface AddFieldPageProps {
  index: RegionIndex | null;
  regionId: string;
}

export function AddFieldPage({ index, regionId }: AddFieldPageProps) {
  const [now] = useState(() => new Date());
  const years = useMemo(() => getRecentHarvestYears(now), [now]);

  const [form, setForm] = useState<CustomFieldFormData>(() => getDefaultFormData(now));
  const [latInput, setLatInput] = useState<string>("");
  const [lonInput, setLonInput] = useState<string>("");
  const [checked, setChecked] = useState<boolean>(false);
  const [isSupported, setIsSupported] = useState<boolean>(false);
  const [liveProfile, setLiveProfile] = useState<LiveClimateProfile | null>(null);
  const [loadingClimate, setLoadingClimate] = useState<boolean>(false);

  const [savedFields, setSavedFields] = useState<CustomFieldRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [csvErrors, setCsvErrors] = useState<string[]>([]);
  const [csvSuccess, setCsvSuccess] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const jsonImportRef = useRef<HTMLInputElement>(null);

  // Load saved fields from device on mount
  useEffect(() => {
    setSavedFields(loadSavedFields());
  }, []);

  // Update coverage status when lat/lon inputs change
  const handleCheckLocation = (lat: number, lon: number) => {
    const supported = isInsideKansasTile(lon, lat);
    setIsSupported(supported);
    setChecked(true);
    setLiveProfile(null);
    setForm((prev) => ({
      ...prev,
      latitude: lat,
      longitude: lon,
    }));
  };

  const handleApplyPreset = (lat: number, lon: number) => {
    setLatInput(String(lat));
    setLonInput(String(lon));
    handleCheckLocation(lat, lon);
  };

  const handleManualCheck = () => {
    const lat = parseFloat(latInput);
    const lon = parseFloat(lonInput);
    if (isNaN(lat) || isNaN(lon)) {
      setChecked(true);
      setIsSupported(false);
      return;
    }
    handleCheckLocation(lat, lon);
  };

  // Find nearest analysed field from Kansas pilot pack
  const nearestResult = useMemo(() => {
    if (form.latitude === null || form.longitude === null || !index?.fields) {
      return null;
    }
    return findNearestAnalysedField(form.latitude, form.longitude, index.fields);
  }, [form.latitude, form.longitude, index]);

  // Save to device storage
  const handleSaveField = () => {
    if (form.latitude === null || form.longitude === null) {
      alert(t("addfield.alertNoCoords"));
      return;
    }
    const record = convertFormToRecord(form, isSupported, selectedId ?? undefined);
    const success = saveCustomField(record);
    if (success) {
      setSavedFields(loadSavedFields());
      setSelectedId(record.id);
      setSaveStatus(t("addfield.save.success"));
      setTimeout(() => setSaveStatus(null), 3500);
    }
  };

  // Switch to an existing saved field
  const handleSelectSaved = (f: CustomFieldRecord) => {
    setSelectedId(f.id);
    setLatInput(String(f.coordinates.latitude));
    setLonInput(String(f.coordinates.longitude));
    setIsSupported(f.is_supported);
    setChecked(true);

    const formData: CustomFieldFormData = {
      name: f.name,
      latitude: f.coordinates.latitude,
      longitude: f.coordinates.longitude,
      seasons: f.seasons.map((s) => ({
        harvest_year: s.harvest_year,
        crop: s.crop,
        sowing: s.sowing,
      })),
      irrigation: {
        is_irrigated: f.irrigation.is_irrigated,
        amount: f.irrigation.input_unit === "in" && f.irrigation.amount_mm !== null
          ? Math.round((f.irrigation.amount_mm / 25.4) * 10) / 10
          : f.irrigation.amount_mm,
        unit: f.irrigation.input_unit,
      },
      soil_tests: {
        organic_matter_pct: f.soil_tests.organic_matter_pct,
        ph: f.soil_tests.ph,
        cec: f.soil_tests.cec,
        notes: f.soil_tests.notes,
      },
      priorities: { ...f.priorities },
      constraints: {
        can_sell: [...f.constraints.can_sell],
        cant_grow: [...f.constraints.cant_grow],
        water_cap_mm: f.constraints.water_cap_mm,
        notes: f.constraints.notes,
      },
    };
    setForm(formData);
  };

  const handleDeleteSaved = (id: string) => {
    deleteCustomField(id);
    const remaining = loadSavedFields();
    setSavedFields(remaining);
    if (selectedId === id) {
      setSelectedId(null);
      setForm(getDefaultFormData(now));
      setLatInput("");
      setLonInput("");
      setChecked(false);
    }
  };

  const handleClearAll = () => {
    if (window.confirm(t("addfield.saved.confirmClear"))) {
      clearAllCustomFields();
      setSavedFields([]);
      setSelectedId(null);
      setForm(getDefaultFormData(now));
      setLatInput("");
      setLonInput("");
      setChecked(false);
    }
  };

  // CSV template download
  const handleDownloadCsv = () => {
    const csvContent = generateCsvTemplate(now);
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fieldwitness_field_template_${years[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // CSV upload handler
  const handleCsvUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvErrors([]);
    setCsvSuccess(null);

    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = String(evt.target?.result ?? "");
      const res = parseCsvInput(text, now);
      if (res.errors.length > 0) {
        setCsvErrors(res.errors);
      } else if (res.data) {
        setForm(res.data);
        if (res.data.latitude !== null && res.data.longitude !== null) {
          setLatInput(String(res.data.latitude));
          setLonInput(String(res.data.longitude));
          handleCheckLocation(res.data.latitude, res.data.longitude);
        }
        setCsvSuccess(t("addfield.csvParsedOk"));
      }
    };
    reader.readAsText(file);
    if (e.target) e.target.value = "";
  };

  // JSON export
  const handleExportJson = () => {
    const jsonStr = exportFieldsAsJson();
    const blob = new Blob([jsonStr], { type: "application/json;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "fieldwitness_saved_fields.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  // JSON import
  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = String(evt.target?.result ?? "");
      const res = importFieldsFromJson(text);
      if (res.errors.length > 0) {
        alert(res.errors.join("\n"));
      } else {
        setSavedFields(loadSavedFields());
        alert(t("addfield.jsonImported", { n: res.imported }));
      }
    };
    reader.readAsText(file);
    if (e.target) e.target.value = "";
  };

  return (
    <article className="add-field-page" aria-labelledby="addfield-h">
      <header className="page-header">
        <h2 id="addfield-h">
          {t("addfield.title")}{" "}
          <span className="tag-pill tag-E" title={t("addfield.tagTitle")}>
            E
          </span>
        </h2>
        <p className="subtitle">{t("addfield.intro")}</p>
        <p className="fixed-line">{t("fixed.judgment")}</p>
      </header>

      {/* SECTION 1: Location & Coverage Check */}
      <section className="card-box" aria-labelledby="loc-h">
        <h3 id="loc-h">
          {t("addfield.check.heading")} <Explain id="global_eval" />
        </h3>
        <p className="muted">{t("addfield.check.help")}</p>

        <div className="presets-bar">
          <span className="presets-label">{t("addfield.presets")}:</span>
          {PRESET_LOCATIONS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className="preset-btn"
              onClick={() => {
                handleApplyPreset(preset.latitude, preset.longitude);
                emitTour(`preset:${preset.id}`);
              }}
            >
              {t(`addfield.preset.${preset.id}` as StringKey)}
            </button>
          ))}
        </div>

        <div className="coord-inputs-row">
          <label className="coord-label">
            <span>{t("addfield.lat")}</span>
            <input
              type="number"
              step="0.0001"
              value={latInput}
              placeholder={t("addfield.latPlaceholder")}
              onChange={(e) => setLatInput(e.target.value)}
            />
          </label>
          <label className="coord-label">
            <span>{t("addfield.lon")}</span>
            <input
              type="number"
              step="0.0001"
              value={lonInput}
              placeholder={t("addfield.lonPlaceholder")}
              onChange={(e) => setLonInput(e.target.value)}
            />
          </label>
          <button type="button" className="action-btn" onClick={handleManualCheck}>
            {t("addfield.check.btn")}
          </button>
        </div>

        {checked && !isSupported && (
          <div className="coverage-alert-box error" role="alert">
            <h4 className="alert-heading">{t("addfield.unsupported.error")}</h4>
            <p className="alert-body">{t("addfield.unsupported.areas")}</p>
          </div>
        )}

        {checked && isSupported && (
          <div className="coverage-alert-box success">
            <h4 className="alert-heading">{t("addfield.supported.title")}</h4>
            <p className="alert-body">{t("addfield.supported.desc")}</p>
          </div>
        )}

        {checked && form.latitude !== null && form.longitude !== null && (
          <div className="global-eval-action" style={{ marginTop: "1rem" }}>
            <button
              type="button"
              className="action-btn"
              onClick={async () => {
                if (form.latitude !== null && form.longitude !== null) {
                  setLoadingClimate(true);
                  try {
                    const irrMm =
                      form.irrigation.is_irrigated === "yes" && form.irrigation.amount != null
                        ? form.irrigation.unit === "in"
                          ? form.irrigation.amount * 25.4
                          : form.irrigation.amount
                        : 0;
                    const prof = await fetchLiveClimateProfile(form.latitude, form.longitude, {
                      irrigationBudgetMm: irrMm,
                      cantGrow: form.constraints.cant_grow,
                      organicMatterPct: form.soil_tests.organic_matter_pct,
                    });
                    setLiveProfile(prof);
                    setActiveLiveClimateProfile(prof);
                  } finally {
                    setLoadingClimate(false);
                  }
                }
              }}
              disabled={loadingClimate}
            >
              {loadingClimate ? t("addfield.eval.loading") : t("addfield.eval.btn")}
            </button>
          </div>
        )}

        {liveProfile && (
          <div className="card-box global-profile-card" aria-label={t("addfield.eval.title", { mode: liveProfile.simulationMode })} style={{ marginTop: "1rem", borderInlineStart: "4px solid var(--accent)" }}>
            <h3>
              {t("addfield.eval.title", { mode: liveProfile.simulationMode })}{" "}
              <Explain id="global_eval" />
            </h3>
            <div className="climate-meta-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))", gap: "0.75rem", margin: "0.75rem 0" }}>
              <div className="climate-stat">
                <span className="stat-label" style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)" }}>{t("addfield.eval.zone", { years: liveProfile.yearsEvaluated })}</span>
                <strong>{liveProfile.climateZone}</strong>
              </div>
              <div className="climate-stat">
                <span className="stat-label" style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)" }}>{t("addfield.eval.rain")}</span>
                <strong>{liveProfile.annualPrecipitationMm} {t("unit.mm")} [O/D]</strong>
              </div>
              <div className="climate-stat">
                <span className="stat-label" style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)" }}>{t("addfield.eval.eto")}</span>
                <strong>{liveProfile.annualEtoMm} {t("unit.mm")} [D]</strong>
              </div>
              <div className="climate-stat">
                <span className="stat-label" style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)" }}>{t("addfield.eval.deficit", { aridity: liveProfile.aridityIndex })}</span>
                <strong>{liveProfile.waterDeficitMm} {t("unit.mm")} [D]</strong>
              </div>
              <div className="climate-stat">
                <span className="stat-label" style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)" }}>
                  {t("addfield.eval.soilAws", { texture: liveProfile.soilContext.textureClass })}{" "}
                  <Explain id="available_water_capacity" />
                </span>
                <strong>{liveProfile.soilContext.estimatedAweMm} {t("unit.mm")} {liveProfile.soilContext.tag}</strong>
              </div>
              <div className="climate-stat">
                <span className="stat-label" style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)" }}>{t("addfield.eval.soilSrc")}</span>
                <strong>{liveProfile.soilContext.source}</strong>
              </div>
            </div>

            <h4 style={{ margin: "0.75rem 0 0.25rem", fontSize: "0.95rem" }}>{t("addfield.eval.rotations")}</h4>
            <ul className="global-rotation-list" style={{ paddingInlineStart: "1.2rem", margin: "0.25rem 0" }}>
              {liveProfile.recommendedRotations.map((r, i) => (
                <li key={i} style={{ marginBottom: "0.5rem", fontSize: "0.88rem" }}>
                  <strong>#{i + 1} {r.name}</strong> — RYI: <strong>{r.ryi}</strong> [D] · {t("metric.water_use_mm")}: <strong>{r.waterUseMm} {t("unit.mm")}</strong> ({t("metric.bad_year_water_mm")}: {r.badYearWaterMm} {t("unit.mm")}) [D] · {t("explain.bare_soil_months.title")}: {r.bareMonths} — {r.rationale}
                </li>
              ))}
            </ul>
            <p className="disclaimer-mandatory" style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "var(--muted)" }}>
              {t("addfield.eval.disclaimer", { source: liveProfile.source })}
            </p>
          </div>
        )}
      </section>

      {/* NEAREST ANALYSED FIELD (If coordinates checked) */}
      {checked && nearestResult && (
        <section className="card-box nearest-field-box" aria-labelledby="nearest-h">
          <h3 id="nearest-h">{t("addfield.nearest.label")}</h3>
          <div className="nearest-field-content">
            <div className="nearest-field-header">
              <span className="field-badge">{t("addfield.nearest.pilot", { num: nearestResult.fieldNumber })}</span>
              <span className="field-dist">
                <strong>{t("addfield.nearest.dist", { km: nearestResult.distanceKm })}</strong>
              </span>
              <span className="field-ha">{nearestResult.field.area_ha} {t("unit.ha")}</span>
            </div>

            <p className="disclaimer-mandatory">{t("addfield.nearest.disclaimer")}</p>
            {nearestResult.farDisclaimer && (
              <p className="disclaimer-far" role="note">
                {t("addfield.nearest.farDisclaimer")}
              </p>
            )}

            <div className="nearest-action">
              <a
                href={routeHref(regionId, nearestResult.field.field_id)}
                className="view-field-link"
              >
                {t("addfield.nearest.viewBtn")} →
              </a>
            </div>
          </div>
        </section>
      )}

      {/* SECTION 2: Farm History & Practices */}
      <section className="card-box" aria-labelledby="history-h">
        <h3 id="history-h">{t("addfield.form.heading")}</h3>
        <p className="muted">{t("addfield.form.help")}</p>

        <label className="field-row">
          <span className="field-label">{t("addfield.fieldName")}:</span>
          <input
            type="text"
            className="text-input"
            value={form.name}
            placeholder={t("addfield.namePlaceholder")}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>

        <div className="seasons-grid">
          {form.seasons.map((season, idx) => {
            const seasonLabels = [
              t("addfield.seasonLast", { year: season.harvest_year }),
              t("addfield.seasonPrev", { year: season.harvest_year }),
              t("addfield.seasonPrev2", { year: season.harvest_year }),
            ];
            return (
              <fieldset key={season.harvest_year} className="season-box">
                <legend className="season-legend">
                  {seasonLabels[idx] ?? t("addfield.harvestYear", { year: season.harvest_year })}
                </legend>

                <label className="form-sublabel">
                  <span>{t("addfield.crop")}:</span>
                  <select
                    value={season.crop}
                    onChange={(e) => {
                      const updated = [...form.seasons];
                      updated[idx].crop = e.target.value;
                      setForm({ ...form, seasons: updated });
                    }}
                  >
                    {KANSAS_CROPS.map((c) => (
                      <option key={c.id} value={c.id}>
                        {t(`addfield.cropOpt.${c.id}` as StringKey)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="form-sublabel">
                  <span>{t("addfield.sowing")}:</span>
                  <select
                    value={season.sowing}
                    onChange={(e) => {
                      const updated = [...form.seasons];
                      updated[idx].sowing = e.target.value;
                      setForm({ ...form, seasons: updated });
                    }}
                  >
                    {SOWING_WINDOWS.map((w) => (
                      <option key={w.id} value={w.id}>
                        {t(`addfield.sowing.${w.id}` as StringKey)}
                      </option>
                    ))}
                  </select>
                </label>
              </fieldset>
            );
          })}
        </div>

        {/* IRRIGATION */}
        <fieldset className="sub-fieldset">
          <legend>{t("addfield.irrigation.heading")}</legend>
          <div className="radio-row">
            <span className="radio-label">{t("addfield.irrigation.label")}</span>
            <label className="radio-opt">
              <input
                type="radio"
                name="irrigation_choice"
                value="yes"
                checked={form.irrigation.is_irrigated === "yes"}
                onChange={() =>
                  setForm({
                    ...form,
                    irrigation: { ...form.irrigation, is_irrigated: "yes" },
                  })
                }
              />
              {t("addfield.yes")}
            </label>
            <label className="radio-opt">
              <input
                type="radio"
                name="irrigation_choice"
                value="no"
                checked={form.irrigation.is_irrigated === "no"}
                onChange={() =>
                  setForm({
                    ...form,
                    irrigation: { ...form.irrigation, is_irrigated: "no", amount: null },
                  })
                }
              />
              {t("addfield.no")}
            </label>
            <label className="radio-opt">
              <input
                type="radio"
                name="irrigation_choice"
                value="unknown"
                checked={form.irrigation.is_irrigated === "unknown"}
                onChange={() =>
                  setForm({
                    ...form,
                    irrigation: { ...form.irrigation, is_irrigated: "unknown" },
                  })
                }
              />
              {t("addfield.unknown")}
            </label>
          </div>

          {form.irrigation.is_irrigated === "yes" && (
            <div className="irrigation-amount-row">
              <label className="coord-label">
                <span>{t("addfield.irrigation.amount")}</span>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={form.irrigation.amount ?? ""}
                  placeholder={t("addfield.irrAmountPlaceholder")}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      irrigation: {
                        ...form.irrigation,
                        amount: e.target.value === "" ? null : parseFloat(e.target.value),
                      },
                    })
                  }
                />
              </label>

              <div className="unit-toggle-group">
                <button
                  type="button"
                  className={`toggle-unit-btn ${form.irrigation.unit === "in" ? "active" : ""}`}
                  onClick={() =>
                    setForm({
                      ...form,
                      irrigation: { ...form.irrigation, unit: "in" },
                    })
                  }
                >
                  {t("addfield.irrigation.unit.in")}
                </button>
                <button
                  type="button"
                  className={`toggle-unit-btn ${form.irrigation.unit === "mm" ? "active" : ""}`}
                  onClick={() =>
                    setForm({
                      ...form,
                      irrigation: { ...form.irrigation, unit: "mm" },
                    })
                  }
                >
                  {t("addfield.irrigation.unit.mm")}
                </button>
              </div>
              <span className="muted amount-help">
                {form.irrigation.unit === "in"
                  ? t("addfield.unitHelpIn")
                  : t("addfield.unitHelpMm")}
              </span>
            </div>
          )}
        </fieldset>

        {/* SOIL TESTS (OPTIONAL) */}
        <fieldset className="sub-fieldset">
          <legend>{t("addfield.soil.heading")}</legend>
          <p className="notice-box">{t("addfield.soil.notice")}</p>

          <div className="soil-inputs-grid">
            <label className="coord-label">
              <span>{t("addfield.soil.om")}</span>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={form.soil_tests.organic_matter_pct ?? ""}
                placeholder={t("addfield.omPlaceholder")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    soil_tests: {
                      ...form.soil_tests,
                      organic_matter_pct: e.target.value === "" ? null : parseFloat(e.target.value),
                    },
                  })
                }
              />
            </label>

            <label className="coord-label">
              <span>{t("addfield.soil.ph")}</span>
              <input
                type="number"
                step="0.1"
                min="0"
                max="14"
                value={form.soil_tests.ph ?? ""}
                placeholder={t("addfield.phPlaceholder")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    soil_tests: {
                      ...form.soil_tests,
                      ph: e.target.value === "" ? null : parseFloat(e.target.value),
                    },
                  })
                }
              />
            </label>

            <label className="coord-label">
              <span>{t("addfield.soil.cec")}</span>
              <input
                type="number"
                step="0.1"
                min="0"
                value={form.soil_tests.cec ?? ""}
                placeholder={t("addfield.cecPlaceholder")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    soil_tests: {
                      ...form.soil_tests,
                      cec: e.target.value === "" ? null : parseFloat(e.target.value),
                    },
                  })
                }
              />
            </label>
          </div>
        </fieldset>

        {/* PRIORITIES */}
        <fieldset className="sub-fieldset">
          <legend>{t("addfield.prio.heading")}</legend>
          <div className="sliders-container">
            {PRIORITY_KEYS.map((k: PriorityKey) => (
              <label key={k} className="slider-item">
                <span className="slider-name">{t(`prio.${k}`)}</span>
                <input
                  type="range"
                  min={0}
                  max={3}
                  step={1}
                  value={form.priorities[k]}
                  aria-valuetext={t(`prio.level.${form.priorities[k]}` as "prio.level.0")}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      priorities: { ...form.priorities, [k]: Number(e.target.value) },
                    })
                  }
                />
                <output className="slider-output">
                  {t(`prio.level.${form.priorities[k]}` as "prio.level.0")}
                </output>
              </label>
            ))}
          </div>
          <button
            type="button"
            className="secondary-btn"
            disabled={isDefault(form.priorities)}
            onClick={() => setForm({ ...form, priorities: { ...DEFAULT_PRIORITIES } })}
          >
            {t("prio.reset")}
          </button>
        </fieldset>

        {/* CONSTRAINTS */}
        <fieldset className="sub-fieldset">
          <legend>{t("addfield.cons.heading")}</legend>

          <div className="cons-group">
            <span className="cons-subhead">{t("addfield.cons.canSell")}:</span>
            <div className="checkboxes-wrap">
              {["maize", "winter_wheat", "sorghum", "cover_crop"].map((cId) => (
                <label key={cId} className="checkbox-opt">
                  <input
                    type="checkbox"
                    checked={form.constraints.can_sell.includes(cId)}
                    onChange={(e) => {
                      const cur = form.constraints.can_sell;
                      const next = e.target.checked
                        ? [...cur, cId]
                        : cur.filter((x) => x !== cId);
                      setForm({
                        ...form,
                        constraints: { ...form.constraints, can_sell: next },
                      });
                    }}
                  />
                  {cropName(cId)}
                </label>
              ))}
            </div>
          </div>

          <div className="cons-group">
            <span className="cons-subhead">{t("addfield.cons.cantGrow")}:</span>
            <div className="checkboxes-wrap">
              {["maize", "winter_wheat", "sorghum", "cover_crop"].map((cId) => (
                <label key={cId} className="checkbox-opt">
                  <input
                    type="checkbox"
                    checked={form.constraints.cant_grow.includes(cId)}
                    onChange={(e) => {
                      const cur = form.constraints.cant_grow;
                      const next = e.target.checked
                        ? [...cur, cId]
                        : cur.filter((x) => x !== cId);
                      setForm({
                        ...form,
                        constraints: { ...form.constraints, cant_grow: next },
                      });
                    }}
                  />
                  {cropName(cId)}
                </label>
              ))}
            </div>
          </div>

          <label className="field-row">
            <span className="field-label">{t("addfield.cons.waterCap")}:</span>
            <input
              type="number"
              className="text-input num-short"
              min="0"
              value={form.constraints.water_cap_mm ?? ""}
              placeholder={t("addfield.waterCapPlaceholder")}
              onChange={(e) =>
                setForm({
                  ...form,
                  constraints: {
                    ...form.constraints,
                    water_cap_mm: e.target.value === "" ? null : parseFloat(e.target.value),
                  },
                })
              }
            />
          </label>

          <label className="field-row-col">
            <span className="field-label">{t("addfield.cons.notes")}:</span>
            <textarea
              className="notes-textarea"
              rows={3}
              value={form.constraints.notes}
              placeholder={t("addfield.notesPlaceholder")}
              onChange={(e) =>
                setForm({
                  ...form,
                  constraints: { ...form.constraints, notes: e.target.value },
                })
              }
            />
          </label>
        </fieldset>

        <div className="save-action-bar">
          <button type="button" className="primary-save-btn" onClick={handleSaveField}>
            {t("addfield.save.btn")}
          </button>
          {saveStatus && <span className="save-status-msg">{saveStatus}</span>}
        </div>
      </section>

      {/* SECTION 3: Offline CSV Template & Upload */}
      <section className="card-box" aria-labelledby="csv-h">
        <h3 id="csv-h">{t("addfield.csv.heading")}</h3>
        <p className="muted">{t("addfield.csvHelp")}</p>

        <div className="csv-actions-row">
          <button type="button" className="action-btn" onClick={handleDownloadCsv}>
            {t("addfield.csv.download")}
          </button>

          <label className="upload-btn-label">
            {t("addfield.csv.upload")}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: "none" }}
              onChange={handleCsvUpload}
            />
          </label>
        </div>

        {csvSuccess && <p className="csv-success-msg">{csvSuccess}</p>}
        {csvErrors.length > 0 && (
          <div className="csv-errors-box" role="alert">
            <p className="error-title">{t("addfield.csvErrorsTitle")}</p>
            <ul>
              {csvErrors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* SECTION 4: Saved Fields on Device */}
      <section className="card-box" aria-labelledby="saved-h">
        <div className="saved-header-row">
          <h3 id="saved-h">{t("addfield.saved.heading")} ({savedFields.length})</h3>
          <div className="saved-controls">
            <button
              type="button"
              className="secondary-btn"
              disabled={savedFields.length === 0}
              onClick={handleExportJson}
            >
              {t("addfield.saved.export")}
            </button>
            <label className="secondary-btn-label">
              {t("addfield.saved.import")}
              <input
                ref={jsonImportRef}
                type="file"
                accept=".json,application/json"
                style={{ display: "none" }}
                onChange={handleImportJson}
              />
            </label>
            <button
              type="button"
              className="danger-btn"
              disabled={savedFields.length === 0}
              onClick={handleClearAll}
            >
              {t("addfield.saved.clear")}
            </button>
          </div>
        </div>

        {savedFields.length === 0 ? (
          <p className="muted">{t("addfield.savedEmpty")}</p>
        ) : (
          <ul className="saved-list">
            {savedFields.map((f) => (
              <li
                key={f.id}
                className={`saved-item ${selectedId === f.id ? "selected" : ""}`}
              >
                <div className="saved-item-info">
                  <span className="saved-name">{f.name}</span>
                  <span className="saved-coords" dir="ltr">
                    {Math.abs(f.coordinates.latitude).toFixed(4)}°{f.coordinates.latitude >= 0 ? "N" : "S"},{" "}
                    {Math.abs(f.coordinates.longitude).toFixed(4)}°{f.coordinates.longitude >= 0 ? "E" : "W"}
                  </span>
                  <span className={`saved-tag ${f.is_supported ? "tag-ok" : "tag-out"}`}>
                    {f.is_supported ? t("addfield.supportedBadge") : t("addfield.unsupportedBadge")}
                  </span>
                </div>
                <div className="saved-item-actions">
                  <button
                    type="button"
                    className="select-item-btn"
                    onClick={() => handleSelectSaved(f)}
                  >
                    {t("addfield.viewEdit")}
                  </button>
                  <button
                    type="button"
                    className="delete-item-btn"
                    onClick={() => handleDeleteSaved(f.id)}
                    aria-label={t("addfield.deleteLabel", { name: f.name })}
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
