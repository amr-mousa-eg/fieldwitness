import { useSyncExternalStore } from "react";

export type Locale = "en" | "ar";

const STORAGE_KEY = "fw-locale";
const listeners = new Set<() => void>();

let currentLocale: Locale = (() => {
  try {
    if (typeof localStorage !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "ar" || saved === "en") return saved;
    }
  } catch {
    // ignore storage errors
  }
  return "en";
})();

export function applyLocaleToDocument(locale: Locale): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (root) {
    root.lang = locale;
    root.dir = locale === "ar" ? "rtl" : "ltr";
  }
}

applyLocaleToDocument(currentLocale);

export function getLocale(): Locale {
  return currentLocale;
}

export function setLocale(locale: Locale): void {
  if (locale !== "en" && locale !== "ar") return;
  if (currentLocale === locale) return;
  currentLocale = locale;
  applyLocaleToDocument(locale);
  try {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(STORAGE_KEY, locale);
    }
  } catch {
    // ignore storage errors
  }
  for (const fn of listeners) fn();
}

export function subscribeLocale(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useLocale(): Locale {
  return useSyncExternalStore(subscribeLocale, getLocale, () => "en");
}
