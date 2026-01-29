import { useMemo } from "react";

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function valueToAngle(v) {
  return 180 + (v / 100) * 180;
}

function polarToXY(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export default function Wheel({ guess, target, leftLabel, rightLabel, onChange, disabled }) {
  const w = 520, h = 300;
  const cx = w / 2, cy = 250;
  const r = 170;

  const guessAngle = useMemo(() => valueToAngle(clamp(guess, 0, 100)), [guess]);
  const guessPt = useMemo(() => polarToXY(cx, cy, r, guessAngle), [cx, cy, r, guessAngle]);

  const targetAngle = target == null ? null : valueToAngle(clamp(target, 0, 100));
  const targetPt = targetAngle == null ? null : polarToXY(cx, cy, r, targetAngle);

  return (
    <div className="wheelWrap">
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height="260">
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="currentColor"
          strokeWidth="4"
          opacity="0.35"
        />

        <text x={cx - r} y={cy + 28} textAnchor="middle" fontSize="16" opacity="0.8">{leftLabel}</text>
        <text x={cx + r} y={cy + 28} textAnchor="middle" fontSize="16" opacity="0.8">{rightLabel}</text>

        <line x1={cx} y1={cy} x2={guessPt.x} y2={guessPt.y} fill="red" stroke="red" strokeWidth="4" />
        <circle cx={cx} cy={cy} r="6" fill="red" />
        <circle cx={guessPt.x} cy={guessPt.y} r="6" fill="red" />

        {targetPt && (
          <>
            <circle cx={targetPt.x} cy={targetPt.y} r="7" fill="green" stroke="green" strokeWidth="3" />
          </>
        )}
      </svg>

      <div className="sliderRow">
        <input
          type="range"
          min="0"
          max="100"
          value={guess}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          className="slider"
        />
        <div className="guessNum">{guess}</div>
      </div>
    </div>
  );
}

