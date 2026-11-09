import { useEffect, useRef, useState } from "react";
import { t } from "./strings";

export interface TourGuideProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DEMO_FIELD_ID = "0d5615b52572c5c2eeac7fdfef8cdda167050a22";
export const DEMO_REGION_ID = "ks_t14slh";

export interface TourStepDef {
  key: string;
  route: string;
  targetSelector?: string;
  badge: string;
}

export const TOUR_STEPS: TourStepDef[] = [
  {
    key: "step1",
    route: `(#/${DEMO_REGION_ID}/map)`.replace(/[()]/g, ""),
    targetSelector: ".map-container",
    badge: "Kansas T14SLH [B]",
  },
  {
    key: "step2",
    route: `(#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/story)`.replace(/[()]/g, ""),
    targetSelector: ".field-story",
    badge: "Field #12 • Grade B",
  },
  {
    key: "step3",
    route: `(#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/options)`.replace(/[()]/g, ""),
    targetSelector: ".options",
    badge: "Field Card",
  },
  {
    key: "step4",
    route: `(#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/calendar)`.replace(/[()]/g, ""),
    targetSelector: ".calendar-section",
    badge: "Calendar [B/D]",
  },
  {
    key: "step5",
    route: `(#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/advisor)`.replace(/[()]/g, ""),
    targetSelector: ".advisor-console",
    badge: "Advisor Console [D]",
  },
  {
    key: "step6",
    route: `(#/${DEMO_REGION_ID}/${DEMO_FIELD_ID}/sim3d)`.replace(/[()]/g, ""),
    targetSelector: ".sim3d-stage",
    badge: "Simulation 3D [D]",
  },
  {
    key: "step7",
    route: "#/add-field",
    targetSelector: ".addfield-page",
    badge: "Offline & Private",
  },
];

export function TourGuide({ isOpen, onClose }: TourGuideProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [spotlightRect, setSpotlightRect] = useState<DOMRect | null>(null);
  const savedRouteRef = useRef<string>("");
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const nextBtnRef = useRef<HTMLButtonElement | null>(null);

  // When tour opens, record current route so Skip/Escape can restore it exactly
  useEffect(() => {
    if (isOpen) {
      savedRouteRef.current = window.location.hash || "#/";
      setCurrentStep(0);
    }
  }, [isOpen]);

  // Navigate to step route and find target selector
  useEffect(() => {
    if (!isOpen) return;
    const step = TOUR_STEPS[currentStep];
    if (step && window.location.hash !== step.route) {
      window.location.hash = step.route;
    }

    // Attempt to locate spotlight target without fragile dependency
    const updateTargetRect = () => {
      if (!step?.targetSelector) {
        setSpotlightRect(null);
        return;
      }
      try {
        const el = document.querySelector(step.targetSelector);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            setSpotlightRect(rect);
            return;
          }
        }
      } catch {
        // Ignore any selector query errors
      }
      // If target missing or hidden, gracefully skip spotlight
      setSpotlightRect(null);
    };

    updateTargetRect();
    // Re-check shortly after route transition to allow DOM render
    const t1 = setTimeout(updateTargetRect, 250);
    const t2 = setTimeout(updateTargetRect, 600);
    window.addEventListener("resize", updateTargetRect);
    window.addEventListener("scroll", updateTargetRect);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      window.removeEventListener("resize", updateTargetRect);
      window.removeEventListener("scroll", updateTargetRect);
    };
  }, [isOpen, currentStep]);

  // Focus trap inside dialog and initial focus
  useEffect(() => {
    if (isOpen) {
      const focusTimer = setTimeout(() => {
        if (nextBtnRef.current) {
          nextBtnRef.current.focus();
        } else if (dialogRef.current) {
          dialogRef.current.focus();
        }
      }, 100);
      return () => clearTimeout(focusTimer);
    }
  }, [isOpen, currentStep]);

  // Keyboard navigation & trap
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose(true);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNext();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrev();
      } else if (e.key === "Tab") {
        // Focus trap inside dialog
        if (!dialogRef.current) return;
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, currentStep]);

  if (!isOpen) return null;

  const stepDef = TOUR_STEPS[currentStep];
  const isFirst = currentStep === 0;
  const isLast = currentStep === TOUR_STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      handleClose(false);
    } else {
      setCurrentStep((c) => Math.min(c + 1, TOUR_STEPS.length - 1));
    }
  };

  const handlePrev = () => {
    setCurrentStep((c) => Math.max(c - 1, 0));
  };

  const handleClose = (restoreRoute: boolean) => {
    if (restoreRoute && savedRouteRef.current) {
      window.location.hash = savedRouteRef.current;
    }
    onClose();
  };

  return (
    <div className="tour-overlay" role="presentation">
      {/* Visual spotlight cutout if target exists */}
      {spotlightRect && (
        <div
          className="tour-spotlight"
          style={{
            top: `${Math.max(0, spotlightRect.top - 8)}px`,
            left: `${Math.max(0, spotlightRect.left - 8)}px`,
            width: `${spotlightRect.width + 16}px`,
            height: `${spotlightRect.height + 16}px`,
          }}
          aria-hidden="true"
        />
      )}

      {/* Main Tour Dialog Modal */}
      <div
        ref={dialogRef}
        className="tour-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-dialog-title"
        aria-describedby="tour-dialog-body"
        tabIndex={-1}
      >
        <header className="tour-header">
          <div className="tour-step-badge">
            <span className="tour-step-counter">
              {t("tour.step", { current: currentStep + 1, total: TOUR_STEPS.length })}
            </span>
            <span className="tour-tag-badge">{stepDef.badge}</span>
          </div>
          <button
            type="button"
            className="tour-close-btn"
            onClick={() => handleClose(true)}
            aria-label={t("tour.close")}
            title="Exit tour and restore previous view (Escape)"
          >
            ✕
          </button>
        </header>

        <main className="tour-content">
          <h3 id="tour-dialog-title" className="tour-title">
            {t(`tour.${stepDef.key}.title` as any)}
          </h3>
          <p id="tour-dialog-body" className="tour-body">
            {t(`tour.${stepDef.key}.body` as any)}
          </p>
        </main>

        <footer className="tour-footer">
          <button
            type="button"
            className="tour-skip-btn"
            onClick={() => handleClose(true)}
          >
            {t("tour.skip")}
          </button>
          <div className="tour-nav-btns">
            <button
              type="button"
              className="tour-nav-btn tour-prev-btn"
              onClick={handlePrev}
              disabled={isFirst}
            >
              {t("tour.back")}
            </button>
            <button
              ref={nextBtnRef}
              type="button"
              className="tour-nav-btn tour-next-btn"
              onClick={handleNext}
            >
              {isLast ? t("tour.finish") : t("tour.next")}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
