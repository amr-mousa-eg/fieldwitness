function param(name: string): string | null {
  try {
    return new URLSearchParams(window.location.search).get(name);
  } catch {
    return null;
  }
}

/**
 * Rotation Builder: on for everybody. Kill switch: `?builder=0` in the URL (before the #) or
 * VITE_ROTATION_BUILDER=0 at build time.
 */
export function builderEnabled(): boolean {
  if (import.meta.env.VITE_ROTATION_BUILDER === "0") return false;
  return param("builder") !== "0";
}

/** Old links with `?builder=1` open the builder panel straight away. */
export function builderOpenAtStart(): boolean {
  return param("builder") === "1";
}

/**
 * Farm view of Field in 3D: on wherever the builder is on. `?farm=0` is its own kill switch
 * (the glass "Soil X-ray" view is then the only view); `?farm=1` forces it on.
 */
export function farmEnabled(): boolean {
  const v = param("farm");
  if (v === "0") return false;
  if (v === "1") return true;
  return builderEnabled();
}
