import { IS_DEMO_DATA } from "./data";
import { t } from "./strings";

export function DemoBanner() {
  if (!IS_DEMO_DATA) return null;
  return (
    <div className="demo-banner" role="alert">
      {t("demo.banner")}
    </div>
  );
}
