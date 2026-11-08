import { useState } from "react";
import { t } from "./strings";

const STORAGE_KEY = "fw-guidance-dismissed";

function isDismissed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function setDismissed(): void {
  try {
    localStorage.setItem(STORAGE_KEY, "true");
  } catch {
    // blocked or unavailable
  }
}

export function GuidancePanel() {
  const [dismissed, setLocalDismissed] = useState(isDismissed);

  if (dismissed) return null;

  return (
    <aside className="guidance-panel" aria-labelledby="guidance-title">
      <div className="guidance-header">
        <h3 id="guidance-title">{t("guidance.title")}</h3>
        <button
          type="button"
          className="guidance-close"
          onClick={() => {
            setDismissed();
            setLocalDismissed(true);
          }}
          aria-label={t("guidance.dismiss.aria")}
        >
          ×
        </button>
      </div>
      <div className="guidance-body">
        <p>{t("guidance.fields")}</p>
        <p>{t("guidance.grades")}</p>
        <p className="fixed-line">{t("fixed.judgment")}</p>
      </div>
      <button
        type="button"
        className="guidance-dismiss-btn"
        onClick={() => {
          setDismissed();
          setLocalDismissed(true);
        }}
      >
        {t("guidance.dismiss")}
      </button>
    </aside>
  );
}
