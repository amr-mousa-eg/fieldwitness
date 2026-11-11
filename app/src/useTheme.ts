import { useSyncExternalStore } from "react";
import { type ThemeChoice, getEffectiveTheme, getStoredTheme, setStoredTheme, subscribeTheme } from "./theme";

/**
 * The Light / Dark / Auto choice and the effective theme, shared by every component: a change in
 * the toggle (or the system setting) re-renders all users at once, without a reload.
 */
export function useTheme() {
  const choice = useSyncExternalStore<ThemeChoice>(subscribeTheme, getStoredTheme, () => "system");
  const effective = useSyncExternalStore<"light" | "dark">(subscribeTheme, () => getEffectiveTheme(), () => "light");
  return { choice, effective, setChoice: setStoredTheme };
}
