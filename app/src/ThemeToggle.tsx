import { t } from "./strings";
import { useTheme } from "./useTheme";

export function ThemeToggle() {
  const { choice, setChoice } = useTheme();

  return (
    <div className="theme-toggle" role="group" aria-label={t("theme.label")}>
      <button
        type="button"
        className={`theme-btn ${choice === "system" ? "active" : ""}`}
        onClick={() => setChoice("system")}
        aria-pressed={choice === "system"}
        title={t("theme.system")}
      >
        {t("theme.system")}
      </button>
      <button
        type="button"
        className={`theme-btn ${choice === "light" ? "active" : ""}`}
        onClick={() => setChoice("light")}
        aria-pressed={choice === "light"}
        title={t("theme.light")}
      >
        ☀ {t("theme.light")}
      </button>
      <button
        type="button"
        className={`theme-btn ${choice === "dark" ? "active" : ""}`}
        onClick={() => setChoice("dark")}
        aria-pressed={choice === "dark"}
        title={t("theme.dark")}
      >
        ☾ {t("theme.dark")}
      </button>
    </div>
  );
}
