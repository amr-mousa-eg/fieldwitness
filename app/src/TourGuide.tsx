import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import "./TourGuide.css";
import { type StringKey, t } from "./strings";
import {
  TOUR_STEPS,
  browserStorage,
  clearProgress,
  emptyProgress,
  findTargets,
  goToStep,
  isStepDone,
  loadProgress,
  recordAction,
  restoreHash,
  saveProgress,
  stepEntryHash,
  type TourProgress,
} from "./tour";
import { onTourAction } from "./tourEvents";

export { DEMO_FIELD_ID, DEMO_REGION_ID, TOUR_STEPS } from "./tour";

export interface TourGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

/** Attribute that outlines the real control of the current step (styled in TourGuide.css). */
const MARK = "data-tour-target";
const POLL_MS = 400;

function clearMarks(): void {
  document.querySelectorAll(`[${MARK}]`).forEach((el) => el.removeAttribute(MARK));
}

/**
 * "Try it" tour: a small card docked at the bottom (a bottom sheet on phones). No overlay and no
 * focus trap: the app stays usable. Each step outlines the real control, listens for the action
 * (tourEvents.ts) and shows a tick. Next always works; Skip and Escape return to the page the
 * tour started on. Progress is kept in localStorage.
 */
export function TourGuide({ isOpen, onClose }: TourGuideProps) {
  const [progress, setProgress] = useState<TourProgress>(() => loadProgress(browserStorage()));
  const [hasTarget, setHasTarget] = useState(true);
  const startHash = useRef<string>(typeof window !== "undefined" ? window.location.hash || "#/" : "#/");
  const cardRef = useRef<HTMLElement | null>(null);
  const scrolledStep = useRef<number>(-1);

  const step = TOUR_STEPS[progress.step];
  const done = isStepDone(step, progress.done);
  const isFirst = progress.step === 0;
  const isLast = progress.step === TOUR_STEPS.length - 1;

  // Listen for real actions while the tour is open.
  useEffect(() => {
    if (!isOpen) return;
    return onTourAction(window, (a) => setProgress((p) => recordAction(p, a)));
  }, [isOpen]);

  // Remember progress (every change).
  useEffect(() => {
    if (isOpen) saveProgress(browserStorage(), progress);
  }, [isOpen, progress]);

  // Entering a step that happens on a field page: open the demo field if no field is open.
  useEffect(() => {
    if (!isOpen) return;
    const to = stepEntryHash(step, window.location.hash);
    if (to) window.location.hash = to;
  }, [isOpen, step]);

  // Outline the step's control; re-check as the user moves around (pages load lazily).
  useEffect(() => {
    if (!isOpen) return;
    const mark = () => {
      const { els, primary } = findTargets(document, step);
      document.querySelectorAll(`[${MARK}]`).forEach((el) => {
        if (!els.includes(el)) el.removeAttribute(MARK);
      });
      els.forEach((el) => el.setAttribute(MARK, ""));
      setHasTarget(els.length > 0);
      if (primary && step.scroll && scrolledStep.current !== progress.step) {
        scrolledStep.current = progress.step;
        const r = els[0].getBoundingClientRect();
        const cardTop = cardRef.current?.getBoundingClientRect().top ?? window.innerHeight;
        if (r.top < 0 || r.bottom > cardTop) {
          const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
          els[0].scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
        }
      }
    };
    mark();
    const timer = window.setInterval(mark, POLL_MS);
    window.addEventListener("hashchange", mark);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("hashchange", mark);
      clearMarks();
    };
  }, [isOpen, step, progress.step]);

  // Leave room under the page for the card, so the end of every page can scroll above it.
  useLayoutEffect(() => {
    const card = cardRef.current;
    if (!isOpen || !card) return;
    const root = document.documentElement;
    const set = () => root.style.setProperty("--tour-pad", `${Math.ceil(card.getBoundingClientRect().height) + 16}px`);
    set();
    root.classList.add("tour-open");
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(set) : null;
    ro?.observe(card);
    return () => {
      ro?.disconnect();
      root.classList.remove("tour-open");
      root.style.removeProperty("--tour-pad");
    };
  }, [isOpen]);

  // Move focus to the card once when it opens (not on every step: the user is working the page).
  useEffect(() => {
    if (isOpen) cardRef.current?.focus();
  }, [isOpen]);

  const skip = useCallback(() => {
    clearMarks();
    restoreHash(window.location, startHash.current);
    onClose();
  }, [onClose]);

  const finish = () => {
    clearMarks();
    clearProgress(browserStorage());
    onClose();
  };

  // Escape closes the tour like Skip (unless another control already used the key).
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !e.defaultPrevented) skip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, skip]);

  if (!isOpen) return null;

  const status = done ? t("tour.done") : hasTarget ? t("tour.todo") : t("tour.noTarget");

  return (
    <aside
      ref={cardRef}
      className="tour-card"
      aria-labelledby="tour-card-title"
      tabIndex={-1}
    >
      <header className="tour-header">
        <span className="tour-step-counter">
          {t("tour.step", { current: progress.step + 1, total: TOUR_STEPS.length })}
        </span>
        <div className="tour-progress" aria-hidden="true">
          {TOUR_STEPS.map((s, i) => (
            <span
              key={s.key}
              className={`tour-dot${i === progress.step ? " is-current" : ""}${isStepDone(s, progress.done) ? " is-done" : ""}`}
            />
          ))}
        </div>
        <button type="button" className="tour-close-btn" onClick={skip} aria-label={t("tour.close")}>
          ✕
        </button>
      </header>

      <h2 id="tour-card-title" className="tour-title">
        {t(`tour.${step.key}.title` as StringKey)}
      </h2>
      <p className="tour-body">{t(`tour.${step.key}.body` as StringKey)}</p>

      <ul className="tour-checks">
        {step.requires.map((a) => {
          const ok = progress.done.includes(a);
          return (
            <li key={a} className={ok ? "is-done" : undefined}>
              <span className="tour-tick" aria-hidden="true">
                {ok ? "✓" : ""}
              </span>
              {t(`tour.check.${a}` as StringKey)}
              <span className="sr-only">{ok ? " (done)" : " (not done yet)"}</span>
            </li>
          );
        })}
      </ul>
      <p className={`tour-status${done ? " is-done" : ""}`} role="status">
        {status}
      </p>

      <footer className="tour-footer">
        <div className="tour-aux-btns">
          <button type="button" className="tour-skip-btn" onClick={skip}>
            {t("tour.skip")}
          </button>
          <button
            type="button"
            className="tour-skip-btn"
            onClick={() => setProgress(emptyProgress())}
            disabled={isFirst && progress.done.length === 0}
          >
            {t("tour.restart")}
          </button>
        </div>
        <div className="tour-nav-btns">
          <button
            type="button"
            className="tour-nav-btn tour-prev-btn"
            onClick={() => setProgress((p) => goToStep(p, p.step - 1))}
            disabled={isFirst}
          >
            {t("tour.back")}
          </button>
          <button
            type="button"
            className="tour-nav-btn tour-next-btn"
            onClick={() => (isLast ? finish() : setProgress((p) => goToStep(p, p.step + 1)))}
          >
            {isLast ? t("tour.finish") : t("tour.next")}
          </button>
        </div>
      </footer>
    </aside>
  );
}
