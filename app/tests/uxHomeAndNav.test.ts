import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { HomePage } from "../src/HomePage";
import { ResourcesPage } from "../src/ResourcesPage";
import { TermsPage } from "../src/TermsPage";
import { DATASETS } from "../src/datasets";
import { EXPLAINERS } from "../src/explainers";
import { DOCS_PAGES, PRIMARY_PAGES, pageHref, parseHash } from "../src/route";
import { getLocale, setLocale } from "../src/strings";
import { HOME_LINKS, TEAM_MEMBERS } from "../src/teamConfig";

const SRC = join(import.meta.dirname, "../src");
const css = readFileSync(join(SRC, "styles.css"), "utf8");
const appSource = readFileSync(join(SRC, "App.tsx"), "utf8");

describe("Home Page, NASA-style Docs Dropdown, Split Tabs & Map Scroll", () => {
  it("renders all 5 Assiut STEM School team members, emails, paper downloads, repo link, video slot, and impact cards", () => {
    const prev = getLocale();
    try {
      setLocale("en");
      const html = renderToStaticMarkup(createElement(HomePage, { regionId: "ks_t14slh" }));

      expect(html).toContain(HOME_LINKS.repoUrl);
      expect(html).toContain(HOME_LINKS.paperPdfUrl);
      expect(html).toContain(HOME_LINKS.paperDocxUrl);
      expect(html).toContain("320");
      expect(html).toContain("2021");
      expect(html).toContain("home-video-placeholder");

      expect(TEAM_MEMBERS).toHaveLength(5);
      for (const m of TEAM_MEMBERS) {
        expect(html, m.nameEn).toContain(m.nameEn);
        expect(html, m.email).toContain(m.email);
        expect(html, m.affiliationEn).toContain("Assiut STEM School");
      }

      setLocale("ar");
      const arHtml = renderToStaticMarkup(createElement(HomePage, { regionId: "ks_t14slh" }));
      for (const m of TEAM_MEMBERS) {
        expect(arHtml, m.nameAr).toContain(m.nameAr);
      }
    } finally {
      setLocale(prev);
    }
  });

  it("renders ResourcesPage with all 33 datasets, repo link, and paper downloads", () => {
    const prev = getLocale();
    const prevWin = (globalThis as { window?: unknown }).window;
    (globalThis as { window?: unknown }).window = {
      location: { hash: "#/ks_t14slh/resources" },
      addEventListener() {},
      removeEventListener() {},
    };
    try {
      setLocale("en");
      const html = renderToStaticMarkup(createElement(ResourcesPage));
      expect(html).toContain('id="m-data"');
      expect(html).toContain(HOME_LINKS.repoUrl);
      expect(html).toContain(HOME_LINKS.paperPdfUrl);
      expect(DATASETS).toHaveLength(33);
    } finally {
      setLocale(prev);
      (globalThis as { window?: unknown }).window = prevWin;
    }
  });

  it("renders TermsPage with search input and all EXPLAINERS glossary cards", () => {
    const prev = getLocale();
    const prevWin = (globalThis as { window?: unknown }).window;
    (globalThis as { window?: unknown }).window = {
      location: { hash: "#/ks_t14slh/terms" },
      addEventListener() {},
      removeEventListener() {},
    };
    try {
      setLocale("en");
      const html = renderToStaticMarkup(createElement(TermsPage));
      expect(html).toContain('id="glossary"');
      expect(html).toContain("terms-search-input");
      for (const id of EXPLAINERS) {
        expect(html, id).toContain(`id="glossary-${id}"`);
      }
    } finally {
      setLocale(prev);
      (globalThis as { window?: unknown }).window = prevWin;
    }
  });

  it("groups Methods, Resources, and Terms inside the header dropdown and keeps primary navigation order", () => {
    expect(PRIMARY_PAGES).toEqual(["home", "map", "scoreboard", "compare", "add-field"]);
    expect(DOCS_PAGES).toEqual(["methods", "resources", "terms"]);
    expect(appSource).toContain("nav-dropdown");
    expect(appSource).toContain("nav-dropdown-trigger");
    expect(appSource).toContain("nav-dropdown-menu");
    expect(parseHash("").page).toBe("home");
    expect(parseHash("#/ks_t14slh").page).toBe("map");
    expect(pageHref("ks_t14slh", "home")).toBe("#/home");
  });

  it("locks .app--map to viewport height with flex-constrained .app-main and scrollable .rail", () => {
    expect(css).toMatch(/\.app--map\s*\{[^}]*max-height:\s*100dvh;\s*overflow:\s*hidden;/);
    expect(css).toMatch(/\.app--map\s+\.app-main\s*\{[^}]*min-height:\s*0;\s*overflow:\s*hidden;/);
    expect(css).toMatch(/\.app-main\s*\{[^}]*grid-template-rows:\s*minmax\(0,\s*1fr\);/);
    expect(css).toMatch(/\.rail\s*\{[^}]*min-height:\s*0;\s*overflow-y:\s*auto;/);
  });
});
