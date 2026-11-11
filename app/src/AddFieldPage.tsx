import { useEffect, useMemo, useRef, useState } from "react";
import {
  COVERAGE_ERROR_MESSAGE,
  type CustomFieldFormData,
  findNearestAnalysedField,
  generateCsvTemplate,
  getDefaultFormData,
  getRecentHarvestYears,
  isInsideKansasTile,
  KANSAS_CROPS,
  parseCsvInput,
  PRESET_LOCATIONS,
  SOIL_TEST_DISCLAIMER,
  SOWING_WINDOWS,
  SUPPORTED_AREAS_TEXT,
} from "./customField";
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
import { t } from "./strings";
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
      alert("Please enter coordinates and check location before saving.");
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
        setCsvSuccess("CSV record parsed and populated into form successfully.");
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
        alert(`Successfully imported ${res.imported} custom field(s).`);
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
          <span className="tag-pill tag-E" title="Farmer-entered data (tag E)">
            E
          </span>
        </h2>
        <p className="subtitle">{t("addfield.intro")}</p>
        <p className="fixed-line">{t("fixed.judgment")}</p>
      </header>

      {/* SECTION 1: Location & Coverage Check */}
      <section className="card-box" aria-labelledby="loc-h">
        <h3 id="loc-h">{t("addfield.check.heading")}</h3>
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
              {preset.label}
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
              placeholder="e.g. 37.9717"
              onChange={(e) => setLatInput(e.target.value)}
            />
          </label>
          <label className="coord-label">
            <span>{t("addfield.lon")}</span>
            <input
              type="number"
              step="0.0001"
              value={lonInput}
              placeholder="e.g. -100.8727"
              onChange={(e) => setLonInput(e.target.value)}
            />
          </label>
          <button type="button" className="action-btn" onClick={handleManualCheck}>
            {t("addfield.check.btn")}
          </button>
        </div>

        {checked && !isSupported && (
          <div className="coverage-alert-box error" role="alert">
            <h4 className="alert-heading">{COVERAGE_ERROR_MESSAGE}</h4>
            <p className="alert-body">{SUPPORTED_AREAS_TEXT}</p>
          </div>
        )}

        {checked && isSupported && (
          <div className="coverage-alert-box success">
            <h4 className="alert-heading">{t("addfield.supported.title")}</h4>
            <p className="alert-body">{t("addfield.supported.desc")}</p>
          </div>
        )}
      </section>

      {/* NEAREST ANALYSED FIELD (If coordinates checked) */}
      {checked && nearestResult && (
        <section className="card-box nearest-field-box" aria-labelledby="nearest-h">
          <h3 id="nearest-h">{nearestResult.label}</h3>
          <div className="nearest-field-content">
            <div className="nearest-field-header">
              <span className="field-badge">Pilot Field {nearestResult.fieldNumber}</span>
              <span className="field-dist">
                <strong>{nearestResult.distanceKm} km</strong> from your location
              </span>
              <span className="field-ha">{nearestResult.field.area_ha} ha</span>
            </div>

            <p className="disclaimer-mandatory">{nearestResult.disclaimer}</p>
            {nearestResult.farDisclaimer && (
              <p className="disclaimer-far" role="note">
                {nearestResult.farDisclaimer}
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
            placeholder="e.g. North 80 / Pivot 2"
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>

        <div className="seasons-grid">
          {form.seasons.map((season, idx) => {
            const seasonLabels = [
              `Last season (${season.harvest_year})`,
              `Season before (${season.harvest_year})`,
              `Season before that (${season.harvest_year})`,
            ];
            return (
              <fieldset key={season.harvest_year} className="season-box">
                <legend className="season-legend">{seasonLabels[idx] ?? `Harvest Year ${season.harvest_year}`}</legend>

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
                        {c.label}
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
                        {w.label}
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
              Yes
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
              No
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
              I don't know
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
                  placeholder="e.g. 10"
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
                  ? "(Stored as mm: 1 in = 25.4 mm)"
                  : "(Direct mm)"}
              </span>
            </div>
          )}
        </fieldset>

        {/* SOIL TESTS (OPTIONAL) */}
        <fieldset className="sub-fieldset">
          <legend>{t("addfield.soil.heading")}</legend>
          <p className="notice-box">{SOIL_TEST_DISCLAIMER}</p>

          <div className="soil-inputs-grid">
            <label className="coord-label">
              <span>{t("addfield.soil.om")}</span>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={form.soil_tests.organic_matter_pct ?? ""}
                placeholder="e.g. 2.1"
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
                placeholder="e.g. 7.2"
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
                placeholder="e.g. 18.5"
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
                  {t(`crop.${cId}` as "crop.maize")}
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
                  {t(`crop.${cId}` as "crop.maize")}
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
              placeholder="e.g. 350"
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
              placeholder="e.g. Center pivot irrigation, sandy loam soil; herbicide carryover history"
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
        <p className="muted">
          Download a blank key-value CSV template (UTF-8 BOM compatible with Excel/Sheets), fill it in
          at your convenience offline, and upload it back.
        </p>

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
            <p className="error-title">CSV parsing issues:</p>
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
          <p className="muted">No fields saved on this device yet.</p>
        ) : (
          <ul className="saved-list">
            {savedFields.map((f) => (
              <li
                key={f.id}
                className={`saved-item ${selectedId === f.id ? "selected" : ""}`}
              >
                <div className="saved-item-info">
                  <span className="saved-name">{f.name}</span>
                  <span className="saved-coords">
                    {f.coordinates.latitude.toFixed(4)}°N, {f.coordinates.longitude.toFixed(4)}°W
                  </span>
                  <span className={`saved-tag ${f.is_supported ? "tag-ok" : "tag-out"}`}>
                    {f.is_supported ? "Supported" : "Unsupported"}
                  </span>
                </div>
                <div className="saved-item-actions">
                  <button
                    type="button"
                    className="select-item-btn"
                    onClick={() => handleSelectSaved(f)}
                  >
                    View / Edit
                  </button>
                  <button
                    type="button"
                    className="delete-item-btn"
                    onClick={() => handleDeleteSaved(f.id)}
                    aria-label={`Delete ${f.name}`}
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
