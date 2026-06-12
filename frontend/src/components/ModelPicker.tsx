"use client";

function VignetteModerne() {
  return (
    <div style={{ width: 140, height: 100, backgroundColor: "#FFFFFF", border: "1px solid #D1D5DB", borderRadius: 6, overflow: "hidden", fontFamily: "sans-serif" }}>
      {/* En-tête vert */}
      <div style={{ backgroundColor: "#14532D", padding: "5px 7px", display: "flex", alignItems: "center", gap: 5, minHeight: 26 }}>
        <div style={{ width: 14, height: 14, backgroundColor: "rgba(255,255,255,0.2)", borderRadius: 2, flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <div style={{ color: "#FFFFFF", fontWeight: 700, fontSize: 6.5, lineHeight: 1.2 }}>MON ENTREPRISE BTP</div>
          <div style={{ color: "rgba(255,255,255,0.55)", fontSize: 5.5 }}>SIRET · Tél · Email</div>
        </div>
        <div style={{ color: "#FFFFFF", fontWeight: 800, fontSize: 10, letterSpacing: "0.04em" }}>DEVIS</div>
      </div>
      {/* Blocs client/chantier */}
      <div style={{ display: "flex", gap: 3, padding: "3px 6px 2px" }}>
        <div style={{ flex: 1, backgroundColor: "#F8FAFC", borderRadius: 2, height: 10, borderLeft: "2px solid #14532D" }} />
        <div style={{ flex: 1, backgroundColor: "#FFFBEB", borderRadius: 2, height: 10, borderLeft: "2px solid #F59E0B" }} />
      </div>
      {/* En-tête tableau */}
      <div style={{ backgroundColor: "#14532D", height: 7, margin: "1px 6px", borderRadius: 1 }} />
      {/* Bandeau lot */}
      <div style={{ backgroundColor: "#E3EDE6", height: 6, margin: "2px 6px 1px", borderRadius: 1 }} />
      {/* Lignes fausses */}
      {[0, 1, 2].map(i => (
        <div key={i} style={{ display: "flex", gap: 3, margin: "1.5px 6px", alignItems: "center" }}>
          <div style={{ flex: 3, height: 4, backgroundColor: i % 2 === 0 ? "#F3F4F6" : "#F9FAFB", borderRadius: 1 }} />
          <div style={{ flex: 1, height: 4, backgroundColor: i % 2 === 0 ? "#F3F4F6" : "#F9FAFB", borderRadius: 1 }} />
          <div style={{ width: 18, height: 4, backgroundColor: i % 2 === 0 ? "#D1FAE5" : "#E9F5EC", borderRadius: 1 }} />
        </div>
      ))}
    </div>
  );
}

function VignettePro() {
  return (
    <div style={{ width: 140, height: 100, backgroundColor: "#FFFFFF", border: "1px solid #D1D5DB", borderRadius: 6, overflow: "hidden", fontFamily: "Georgia, serif" }}>
      {/* En-tête blanc + filet anthracite */}
      <div style={{ padding: "5px 7px", borderBottom: "2px solid #1F2937", minHeight: 26, display: "flex", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ color: "#1F2937", fontWeight: 700, fontSize: 7, fontFamily: "Georgia,serif" }}>MON ENTREPRISE BTP</div>
          <div style={{ color: "#9CA3AF", fontSize: 5.5, marginTop: 1 }}>SIRET · Adresse · Tél</div>
        </div>
        <div style={{ color: "#1F2937", fontWeight: 800, fontSize: 11, fontFamily: "Georgia,serif", letterSpacing: "0.03em" }}>DEVIS</div>
      </div>
      {/* Blocs client/chantier */}
      <div style={{ display: "flex", gap: 3, padding: "3px 6px 2px" }}>
        <div style={{ flex: 1, backgroundColor: "#F8FAFC", borderRadius: 2, height: 10, borderLeft: "2px solid #3B5573" }} />
        <div style={{ flex: 1, backgroundColor: "#FFFBEB", borderRadius: 2, height: 10, borderLeft: "2px solid #F59E0B" }} />
      </div>
      {/* En-tête tableau acier */}
      <div style={{ backgroundColor: "#3B5573", height: 7, margin: "1px 6px", borderRadius: 1 }} />
      {/* Lot name acier */}
      <div style={{ color: "#3B5573", fontSize: 5.5, fontWeight: 700, fontFamily: "Georgia,serif", margin: "2px 6px 0", paddingBottom: 1, borderBottom: "0.75px solid #3B5573" }}>LOT MAÇONNERIE</div>
      {/* Lignes fausses */}
      {[0, 1, 2].map(i => (
        <div key={i} style={{ display: "flex", gap: 3, margin: "1.5px 6px", alignItems: "center" }}>
          <div style={{ flex: 3, height: 4, backgroundColor: "#F9FAFB", borderRadius: 1 }} />
          <div style={{ flex: 1, height: 4, backgroundColor: "#F9FAFB", borderRadius: 1 }} />
          <div style={{ width: 18, height: 4, backgroundColor: "#EDF1F5", borderRadius: 1 }} />
        </div>
      ))}
    </div>
  );
}

const VIGNETTES = {
  moderne: { label: "Moderne", Render: VignetteModerne },
  pro:     { label: "Pro",     Render: VignettePro },
};

interface ModelPickerProps {
  value: string;
  onChange: (m: string) => void;
  /** Réduit la vignette à ~90×65 px via CSS scale — adapté aux barres d'outils compactes */
  compact?: boolean;
}

export default function ModelPicker({ value, onChange, compact = false }: ModelPickerProps) {
  const scale  = compact ? 90 / 140 : 1;
  const thumbW = compact ? 90 : 140;
  const thumbH = compact ? Math.round(100 * scale) : 100;

  return (
    <div style={{ display: "flex", gap: compact ? 8 : 14, alignItems: "flex-start" }}>
      {(["moderne", "pro"] as const).map(m => {
        const { label, Render } = VIGNETTES[m];
        const selected = value === m;
        return (
          <button
            key={m}
            type="button"
            onClick={() => onChange(m)}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 6,
              padding: compact ? "4px 5px" : "6px 8px",
              borderRadius: 10,
              border: selected ? "2px solid #14532D" : "2px solid #E5E7EB",
              backgroundColor: selected ? "#F0F7F3" : "#FFFFFF",
              cursor: "pointer",
              transition: "border-color 0.15s, background-color 0.15s",
              outline: "none",
            }}
          >
            {compact ? (
              /* Wrapper taille cible + scale CSS */
              <div style={{ width: thumbW, height: thumbH, overflow: "hidden", flexShrink: 0 }}>
                <div style={{ width: 140, height: 100, transform: `scale(${scale})`, transformOrigin: "top left" }}>
                  <Render />
                </div>
              </div>
            ) : (
              <Render />
            )}
            <span style={{ fontSize: compact ? 11 : 12, fontWeight: 600, color: selected ? "#14532D" : "#5A635D" }}>
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
