import { useEffect, useState } from "react";
import { type ThemeChoice, getEffectiveTheme, getStoredTheme, setStoredTheme } from "./theme";

export function useTheme() {
  const [choice, setChoiceState] = useState<ThemeChoice>(() => getStoredTheme());
  const [effective, setEffective] = useState<"light" | "dark">(() => getEffectiveTheme(choice));

  const setChoice = (newChoice: ThemeChoice) => {
    setChoiceState(newChoice);
    setStoredTheme(newChoice);
    setEffective(getEffectiveTheme(newChoice));
  };

  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const handler = () => {
      if (getStoredTheme() === "system") {
        setEffective(getEffectiveTheme("system"));
      }
    };
    media?.addEventListener?.("change", handler);
    return () => media?.removeEventListener?.("change", handler);
  }, []);

  return { choice, effective, setChoice };
}
