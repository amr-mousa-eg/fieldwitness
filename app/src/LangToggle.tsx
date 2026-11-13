import { getLocale, setLocale, useLocale } from "./locale";
import { t } from "./strings";

export function LangToggle() {
  const locale = useLocale();

  return (
    <div className="lang-toggle" role="group" aria-label={t("lang.label")}>
      <button
        type="button"
        className={`theme-btn ${locale === "en" ? "active" : ""}`}
        onClick={() => setLocale("en")}
        aria-pressed={locale === "en"}
        title="English (LTR)"
      >
        {t("lang.en")}
      </button>
      <button
        type="button"
        className={`theme-btn ${locale === "ar" ? "active" : ""}`}
        onClick={() => setLocale("ar")}
        aria-pressed={locale === "ar"}
        lang="ar"
        title="العربية (RTL)"
      >
        {t("lang.ar")}
      </button>
    </div>
  );
}

export { getLocale, setLocale };
