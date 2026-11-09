export interface DiagramBox {
  id: string;
  label: string;
  sublabel?: string;
  group: "sources" | "story" | "witnesses" | "grading" | "ranking" | "hindcast";
  status?: "ACTIVE" | "OFF";
}

export const DIAGRAM_BOXES: DiagramBox[] = [
  // 1. Data Sources
  { id: "ds_hls", label: "HLS (30 m)", sublabel: "Surface Reflectance & VIs", group: "sources" },
  { id: "ds_power", label: "NASA POWER Weather", sublabel: "Daily Solar, Temp, Rain", group: "sources" },
  { id: "ds_smap", label: "SMAP Soil Moisture", sublabel: "9 km L4 Root-Zone", group: "sources" },
  { id: "ds_grace", label: "GRACE Water Storage", sublabel: "0.5° JPL Mascons", group: "sources" },
  { id: "ds_nasadem", label: "NASADEM Elevation", sublabel: "30 m Slope & Aspect", group: "sources" },
  { id: "ds_gibs", label: "GIBS True-Colour Basemap", sublabel: "HLS S30 Summer 2023", group: "sources" },
  { id: "ds_soilgrids", label: "ISRIC SoilGrids 2.0", sublabel: "250 m Texture & AWC", group: "sources" },
  { id: "ds_csb", label: "USDA CSB Labels", sublabel: "Crop Sequence Geometry", group: "sources" },

  // 2. Pre-processing & Field Story
  { id: "field_story", label: "Field Story", sublabel: "Seasons 2015–2024 (78.3% match)", group: "story" },

  // 3. Three Witnesses
  {
    id: "w1_physics",
    label: "Witness 1: Physics",
    sublabel: "FAO-56 Dual Kc Water Balance",
    status: "ACTIVE",
    group: "witnesses",
  },
  {
    id: "w2_past",
    label: "Witness 2: Own Past",
    sublabel: "ABC Historical Calibration",
    status: "ACTIVE",
    group: "witnesses",
  },
  {
    id: "w3_neighbours",
    label: "Witness 3: Neighbours",
    sublabel: "OFF: no neighbour contrast passed the diagnostic checks (0 of 32)",
    status: "OFF",
    group: "witnesses",
  },

  // 4. Agreement & Grading
  {
    id: "agreement",
    label: "Agreement Engine",
    sublabel: "Evidence Grades A–D (Capped at B)",
    group: "grading",
  },

  // 5. Rotation Engine & Ranking
  {
    id: "rotation_rank",
    label: "Rotation Ranking",
    sublabel: "Pareto Dominance + User Priorities",
    group: "ranking",
  },

  // 6. Hindcast Check
  {
    id: "hindcast_check",
    label: "Hindcast Check",
    sublabel: "Weak skill, underdispersed CIs, beats B1/B2 overall",
    group: "hindcast",
  },
];

export function MethodsDiagram() {
  return (
    <figure className="methods-diagram-wrap" aria-labelledby="methods-diagram-caption">
      <svg
        className="methods-diagram-svg"
        viewBox="0 0 840 510"
        role="img"
        aria-labelledby="diagram-title diagram-desc"
      >
        <title id="diagram-title">FieldWitness Pipeline Data Flow</title>
        <desc id="diagram-desc">
          Architecture diagram showing data flow from NASA and geospatial datasets through the field
          story, the three witnesses (physics, own history, and spatial neighbours marked OFF),
          evidence grading capped at B, rotation ranking, and hindcast validation.
        </desc>

        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="6"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="var(--rule)" />
          </marker>
        </defs>

        {/* Column 1: Data Sources */}
        <text x="20" y="24" className="diagram-col-header">
          Data Sources (8)
        </text>

        {/* ds_hls */}
        <g id="box-ds_hls">
          <rect x="20" y="35" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="52" className="diagram-box-title">HLS (30 m)</text>
          <text x="28" y="67" className="diagram-box-sub">Surface Reflectance & VIs</text>
        </g>

        {/* ds_power */}
        <g id="box-ds_power">
          <rect x="20" y="85" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="102" className="diagram-box-title">NASA POWER Weather</text>
          <text x="28" y="117" className="diagram-box-sub">Daily Solar, Temp, Rain</text>
        </g>

        {/* ds_smap */}
        <g id="box-ds_smap">
          <rect x="20" y="135" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="152" className="diagram-box-title">SMAP Soil Moisture</text>
          <text x="28" y="167" className="diagram-box-sub">9 km L4 Root-Zone</text>
        </g>

        {/* ds_grace */}
        <g id="box-ds_grace">
          <rect x="20" y="185" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="202" className="diagram-box-title">GRACE Water Storage</text>
          <text x="28" y="217" className="diagram-box-sub">0.5° JPL Mascons</text>
        </g>

        {/* ds_nasadem */}
        <g id="box-ds_nasadem">
          <rect x="20" y="235" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="252" className="diagram-box-title">NASADEM Elevation</text>
          <text x="28" y="267" className="diagram-box-sub">30 m Slope & Aspect</text>
        </g>

        {/* ds_gibs */}
        <g id="box-ds_gibs">
          <rect x="20" y="285" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="302" className="diagram-box-title">GIBS True-Colour Basemap</text>
          <text x="28" y="317" className="diagram-box-sub">HLS S30 Summer 2023</text>
        </g>

        {/* ds_soilgrids */}
        <g id="box-ds_soilgrids">
          <rect x="20" y="335" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="352" className="diagram-box-title">ISRIC SoilGrids 2.0</text>
          <text x="28" y="367" className="diagram-box-sub">250 m Texture & AWC</text>
        </g>

        {/* ds_csb */}
        <g id="box-ds_csb">
          <rect x="20" y="385" width="160" height="42" rx="4" className="diagram-box-source" />
          <text x="28" y="402" className="diagram-box-title">USDA CSB Labels</text>
          <text x="28" y="417" className="diagram-box-sub">Crop Sequence Geometry</text>
        </g>

        {/* Connectors Col 1 -> Col 2 */}
        <path d="M 180 56 L 225 155" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 180 406 L 225 175" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 180 106 L 415 65" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 180 356 L 415 75" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />

        {/* Column 2: Story */}
        <text x="230" y="130" className="diagram-col-header">
          Field Story
        </text>
        <g id="box-field_story">
          <rect x="230" y="145" width="150" height="58" rx="6" className="diagram-box-main" />
          <text x="240" y="168" className="diagram-box-title">Field Story</text>
          <text x="240" y="186" className="diagram-box-sub">Seasons 2015–2024</text>
          <text x="240" y="196" className="diagram-box-sub" fill="var(--muted)">(78.3% match vs 90%)</text>
        </g>

        {/* Connectors Col 2 -> Col 3 */}
        <path d="M 380 165 L 420 145" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 380 185 L 420 220" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />

        {/* Column 3: The Three Witnesses */}
        <text x="430" y="24" className="diagram-col-header">
          The Three Witnesses
        </text>

        {/* Witness 1 */}
        <g id="box-w1_physics">
          <rect x="430" y="38" width="190" height="56" rx="6" className="diagram-box-active" />
          <text x="440" y="58" className="diagram-box-title">Witness 1: Physics</text>
          <text x="440" y="73" className="diagram-box-sub">FAO-56 Dual Kc Water Balance</text>
          <text x="440" y="86" className="diagram-tag-active">ACTIVE (Daily soil water)</text>
        </g>

        {/* Witness 2 */}
        <g id="box-w2_past">
          <rect x="430" y="112" width="190" height="56" rx="6" className="diagram-box-active" />
          <text x="440" y="132" className="diagram-box-title">Witness 2: Own Past</text>
          <text x="440" y="147" className="diagram-box-sub">ABC Historical Calibration</text>
          <text x="440" y="160" className="diagram-tag-active">ACTIVE (Credibility score)</text>
        </g>

        {/* Witness 3 */}
        <g id="box-w3_neighbours">
          <rect x="430" y="186" width="190" height="74" rx="6" className="diagram-box-off" />
          <text x="440" y="206" className="diagram-box-title">Witness 3: Neighbours</text>
          <text x="440" y="221" className="diagram-box-sub">Double ML Contrast Effect</text>
          <text x="440" y="236" className="diagram-tag-off">OFF: no neighbour contrast</text>
          <text x="440" y="250" className="diagram-tag-off">passed checks (0 of 32)</text>
        </g>

        {/* Connectors Col 3 -> Col 4 */}
        <path d="M 620 66 L 655 125" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 620 140 L 655 140" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />
        <path d="M 620 214 L 655 155" stroke="var(--rule)" strokeWidth="1.5" strokeDasharray="3 3" markerEnd="url(#arrow)" fill="none" />

        {/* Column 4: Synthesis & Output */}
        <text x="660" y="95" className="diagram-col-header">
          Synthesis & Verification
        </text>

        {/* Agreement */}
        <g id="box-agreement">
          <rect x="660" y="108" width="165" height="54" rx="6" className="diagram-box-main" />
          <text x="670" y="128" className="diagram-box-title">Agreement Engine</text>
          <text x="670" y="143" className="diagram-box-sub">Grades A–D (Capped at B)</text>
          <text x="670" y="155" className="diagram-box-sub" fill="var(--muted)">Witness agreement</text>
        </g>

        {/* Connector Agreement -> Rotation */}
        <path d="M 742 162 L 742 188" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />

        {/* Rotation Ranking */}
        <g id="box-rotation_rank">
          <rect x="660" y="196" width="165" height="58" rx="6" className="diagram-box-main" />
          <text x="670" y="216" className="diagram-box-title">Rotation Ranking</text>
          <text x="670" y="231" className="diagram-box-sub">Pareto + User Priorities</text>
          <text x="670" y="245" className="diagram-box-sub" fill="var(--muted)">Why this ranking? breakdown</text>
        </g>

        {/* Connector Rotation -> Hindcast */}
        <path d="M 742 254 L 742 280" stroke="var(--rule)" strokeWidth="1.5" markerEnd="url(#arrow)" fill="none" />

        {/* Hindcast Check */}
        <g id="box-hindcast_check">
          <rect x="660" y="288" width="165" height="78" rx="6" className="diagram-box-hindcast" />
          <text x="670" y="308" className="diagram-box-title">Hindcast Check</text>
          <text x="670" y="323" className="diagram-box-sub">Frozen as_of(2021-12-31)</text>
          <text x="670" y="337" className="diagram-box-sub" fill="var(--muted)">Weak skill, underdispersed CIs</text>
          <text x="670" y="351" className="diagram-box-sub" fill="var(--muted)">Beats B1/B2 overall (maize only)</text>
        </g>
      </svg>

      <figcaption id="methods-diagram-caption" className="diagram-caption">
        System Architecture: Data flows from NASA and open geospatial inputs through historical field
        phenology, active physics and Bayesian past credibility (Witness 3 OFF due to confounding),
        into evidence-graded rotation options and frozen hindcast evaluation.
      </figcaption>

      {/* Screen-reader accessible semantic fallback */}
      <ol className="sr-only">
        {DIAGRAM_BOXES.map((b) => (
          <li key={b.id}>
            <strong>{b.label}</strong>
            {b.sublabel && <span>: {b.sublabel}</span>}
            {b.status && <em> [{b.status}]</em>}
          </li>
        ))}
      </ol>
    </figure>
  );
}
