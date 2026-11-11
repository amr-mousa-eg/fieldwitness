import { useCallback, useEffect, useRef } from "react";

/**
 * "Try it" tour events. Components announce real user interactions here; the tour (when open)
 * listens and ticks the matching step. Emitting is a no-op when nobody listens.
 */
export const TOUR_EVENT = "fw:tour";

export type TourAction =
  | "field"
  | "season"
  | "priority"
  | "why-ranking"
  | "sim-play"
  | "sim-drought"
  | "limits"
  | `preset:${string}`;

export interface TourEventDetail {
  action: TourAction;
}

export function emitTour(action: TourAction): void {
  if (typeof window === "undefined" || typeof CustomEvent === "undefined") return;
  window.dispatchEvent(new CustomEvent<TourEventDetail>(TOUR_EVENT, { detail: { action } }));
}

/** Subscribe to tour actions on `target` (window in the app). Returns the unsubscribe function. */
export function onTourAction(target: EventTarget, cb: (action: TourAction) => void): () => void {
  const handler = (e: Event) => {
    const action = (e as CustomEvent<Partial<TourEventDetail>>).detail?.action;
    if (typeof action === "string") cb(action);
  };
  target.addEventListener(TOUR_EVENT, handler);
  return () => target.removeEventListener(TOUR_EVENT, handler);
}

/**
 * Emit `action` each time the element comes into the visible part of the screen (the bottom
 * third is left out: the tour card sits there). Used for statements the user has to find.
 */
export function useTourSeen(action: TourAction): (el: Element | null) => void {
  const io = useRef<IntersectionObserver | null>(null);
  // a callback ref, so the observer follows the element even if it mounts after the component
  const ref = useCallback(
    (el: Element | null) => {
      io.current?.disconnect();
      io.current = null;
      if (!el || typeof IntersectionObserver === "undefined") return;
      io.current = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) emitTour(action);
        },
        { rootMargin: "0px 0px -33% 0px", threshold: 0.3 },
      );
      io.current.observe(el);
    },
    [action],
  );
  useEffect(() => () => io.current?.disconnect(), []);
  return ref;
}
