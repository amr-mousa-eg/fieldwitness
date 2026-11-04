import { cropName } from "./strings";

/** A crop sequence as labelled chips; colour supports the label, never replaces it. */
export function CropChips({ sequence }: { sequence: string[] }) {
  return (
    <ol className="crop-chips">
      {sequence.map((c, i) => (
        <li key={i} className={`crop-chip crop-${c}`}>
          {cropName(c)}
        </li>
      ))}
    </ol>
  );
}
