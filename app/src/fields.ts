import type { FieldSummary, Grade } from "./types";

/**
 * Returns a stable map from field_id to a 1-based field number (1..N).
 * Numbering is deterministically ordered by field_id ascending (hash sort).
 */
export function getFieldNumberMap(fields: readonly FieldSummary[]): Map<string, number> {
  const sorted = [...fields].sort((a, b) => a.field_id.localeCompare(b.field_id));
  const map = new Map<string, number>();
  sorted.forEach((f, idx) => map.set(f.field_id, idx + 1));
  return map;
}

/**
 * Returns the stable 1-based number for a single field in a region.
 */
export function fieldNumber(fieldId: string, fields: readonly FieldSummary[]): number {
  const sorted = [...fields].sort((a, b) => a.field_id.localeCompare(b.field_id));
  const idx = sorted.findIndex((f) => f.field_id === fieldId);
  return idx >= 0 ? idx + 1 : 1;
}

/** Rank for sorting by grade: A=4, B=3, C=2, D=1. */
export function gradeRank(grade: Grade): number {
  switch (grade) {
    case "A":
      return 4;
    case "B":
      return 3;
    case "C":
      return 2;
    case "D":
      return 1;
    default:
      return 0;
  }
}
