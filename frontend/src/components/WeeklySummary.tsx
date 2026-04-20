"use client";

type Props = { summary: string; sentiment: string | null };

const SENTIMENT_STYLE: Record<string, string> = {
  positive: "border-green-500/30 bg-green-500/5",
  negative: "border-red-500/30 bg-red-500/5",
  neutral: "border-gray-600/30 bg-gray-800/30",
};

const SENTIMENT_BADGE: Record<string, { label: string; cls: string }> = {
  positive: { label: "긍정적", cls: "bg-green-500/20 text-green-400" },
  negative: { label: "부정적", cls: "bg-red-500/20 text-red-400" },
  neutral: { label: "중립", cls: "bg-gray-700 text-gray-400" },
};

export default function WeeklySummary({ summary, sentiment }: Props) {
  const sent = sentiment || "neutral";
  const badge = SENTIMENT_BADGE[sent] || SENTIMENT_BADGE.neutral;

  return (
    <div className={`rounded-xl p-4 border ${SENTIMENT_STYLE[sent] || SENTIMENT_STYLE.neutral}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold text-gray-300">AI 분석 요약</span>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
          {badge.label}
        </span>
      </div>
      <p className="text-sm text-gray-300 leading-relaxed">{summary}</p>
    </div>
  );
}
