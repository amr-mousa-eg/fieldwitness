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
