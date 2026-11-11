/**
 * Rotation Builder (Level B) is off unless the URL has `?builder=1` (before the #) or the build
 * sets VITE_ROTATION_BUILDER=1. Off by default until it is approved for release.
 */
export function builderEnabled(): boolean {
  if (import.meta.env.VITE_ROTATION_BUILDER === "1") return true;
  try {
    return new URLSearchParams(window.location.search).get("builder") === "1";
  } catch {
    return false;
  }
}

/**
 * Farm view of Field in 3D (isometric farm, two plots): on with `?farm=1`, off with `?farm=0`,
 * otherwise on exactly when the Rotation Builder is on. The Soil X-ray toggle is the glass view.
 */
export function farmEnabled(): boolean {
  try {
    const v = new URLSearchParams(window.location.search).get("farm");
    if (v === "1") return true;
    if (v === "0") return false;
  } catch {
    // no window: fall through
  }
  return builderEnabled();
}
