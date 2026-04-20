"use client";

type Props = { data: Record<string, number> };

const COLORS: Record<string, string> = {
  positive: "#22c55e",
  negative: "#ef4444",
  neutral: "#6b7280",
  cautious: "#f59e0b",
  mixed: "#8b5cf6",
};

const LABELS: Record<string, string> = {
  positive: "긍정",
  negative: "부정",
  neutral: "중립",
  cautious: "신중",
  mixed: "혼재",
};

const HINTS: Record<string, string> = {
  negative: "부정 기사 우세 — 단기 하방 압력 요인",
  positive: "긍정 기조 우세 — 상승 모멘텀 형성 중",
  neutral: "뚜렷한 방향성 없음 — 관망세",
  cautious: "신중론 우세 — 리스크 경계 구간",
  mixed: "엇갈린 시각 혼재 — 변동성 주의",
};

const DISPLAY_ORDER = ["negative", "cautious", "neutral", "mixed", "positive"];

export default function SentimentChart({ data }: Props) {
  const total = Object.values(data ?? {}).reduce((a, b) => a + b, 0);

  const items = DISPLAY_ORDER
    .filter((key) => (data[key] ?? 0) > 0)
    .map((key) => ({
      key,
      name: LABELS[key] || key,
      value: data[key] ?? 0,
      pct: total > 0 ? Math.round(((data[key] ?? 0) / total) * 100) : 0,
      color: COLORS[key] || "#6b7280",
    }));

  const dominant = [...items].sort((a, b) => b.value - a.value)[0];

  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-700/60">
      <h3 className="text-sm font-semibold text-gray-300 mb-1">감성 분포</h3>
      {dominant && (
        <p className="text-xs text-gray-500 mb-4">{HINTS[dominant.key]}</p>
      )}
      <div className="space-y-2.5">
        {items.map((d) => (
          <div key={d.key} className="flex items-center gap-3">
            <div className="w-9 text-xs text-gray-400 flex-shrink-0 text-right">{d.name}</div>
            <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-2 rounded-full transition-all duration-500"
                style={{ width: `${d.pct}%`, backgroundColor: d.color }}
              />
            </div>
            <div className="text-xs text-gray-300 w-7 text-right flex-shrink-0">{d.value}건</div>
            <div className="text-xs text-gray-600 w-8 text-right flex-shrink-0">{d.pct}%</div>
          </div>
        ))}
      </div>
      {total > 0 && (
        <p className="text-xs text-gray-700 mt-3 pt-2 border-t border-gray-800">총 {total}건 분석</p>
      )}
    </div>
  );
}
