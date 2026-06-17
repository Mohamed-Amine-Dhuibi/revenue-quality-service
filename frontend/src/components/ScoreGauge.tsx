import { scoreColor } from "../theme";

// Hand-drawn semicircular gauge (no chart lib) for a crisp hero visual.
export default function ScoreGauge({ score }: { score: number }) {
  const size = 220;
  const stroke = 18;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circ = Math.PI * r; // half circumference
  const clamped = Math.max(0, Math.min(100, score));
  const dash = (clamped / 100) * circ;
  const color = scoreColor(clamped);

  // Semicircle path from left (180°) to right (0°).
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;

  return (
    <div style={{ textAlign: "center" }}>
      <svg width={size} height={size / 2 + 16} viewBox={`0 0 ${size} ${size / 2 + 16}`}>
        <path d={arc} fill="none" stroke="#1c2540" strokeWidth={stroke} strokeLinecap="round" />
        <path
          d={arc}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: "stroke-dasharray 0.8s ease" }}
        />
      </svg>
      <div style={{ marginTop: -size / 2 + 8 }}>
        <div style={{ fontSize: 52, fontWeight: 800, color, letterSpacing: "-0.03em" }}>
          {clamped}
        </div>
        <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Revenue quality / 100
        </div>
      </div>
    </div>
  );
}
