"use client";

import { useEffect, useState } from "react";
import { api, FearGreed } from "@/lib/api";
import { Activity, RefreshCw } from "lucide-react";

const RATING_LABEL: Record<string, string> = {
  "extreme fear": "극공포",
  fear: "공포",
  neutral: "중립",
  greed: "탐욕",
  "extreme greed": "극탐욕",
};

const RATING_COLOR: Record<string, string> = {
  "extreme fear": "text-red-400",
  fear: "text-orange-300",
  neutral: "text-yellow-300",
  greed: "text-green-400",
  "extreme greed": "text-emerald-400",
};

const RATING_BG: Record<string, string> = {
  "extreme fear": "bg-red-500/25 border-red-500/40",
  fear: "bg-orange-500/25 border-orange-400/50",
  neutral: "bg-yellow-500/25 border-yellow-500/40",
  greed: "bg-green-500/25 border-green-500/40",
  "extreme greed": "bg-emerald-500/25 border-emerald-500/40",
};

function ScoreGauge({ score }: { score: number }) {
  // 게이지 바 — 0~100 선형, 5구간 색상
  const segments = [
    { label: "극공포", color: "#ef4444", from: 0, to: 25 },
    { label: "공포", color: "#f97316", from: 25, to: 45 },
    { label: "중립", color: "#eab308", from: 45, to: 55 },
    { label: "탐욕", color: "#22c55e", from: 55, to: 75 },
    { label: "극탐욕", color: "#16a34a", from: 75, to: 100 },
  ];

  return (
    <div className="space-y-1.5">
      {/* 게이지 바 */}
      <div className="relative h-3 rounded-full overflow-hidden flex">
        {segments.map((s) => (
          <div
            key={s.label}
            style={{
              width: `${s.to - s.from}%`,
              backgroundColor: s.color,
            }}
          />
        ))}
        {/* 현재 위치 마커 */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg"
          style={{ left: `${Math.min(98, Math.max(1, score))}%` }}
        />
      </div>
      {/* 라벨: 각 구간의 중앙에 배치 */}
      <div className="relative h-4 text-[10px] text-gray-500">
        {segments.map((s) => (
          <span
            key={s.label}
            className="absolute top-0 -translate-x-1/2 whitespace-nowrap"
            style={{ left: `${(s.from + s.to) / 2}%` }}
          >
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function MiniBar({ label, value, prevValue }: { label: string; value: number | null; prevValue: number | null }) {
  if (value === null) return null;
  const change = prevValue !== null ? value - prevValue : null;
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <div className="flex items-center gap-1.5">
        <span className="text-gray-300">{value}</span>
        {change !== null && (
          <span className={change > 0 ? "text-green-400" : change < 0 ? "text-red-400" : "text-gray-500"}>
            {change > 0 ? `+${change.toFixed(1)}` : change.toFixed(1)}
          </span>
        )}
      </div>
    </div>
  );
}

export default function FearGreedCard() {
  const [data, setData] = useState<FearGreed | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = (refresh: boolean) => {
    api.fearGreed(refresh)
      .then(setData)
      .catch(() => {})
      .finally(() => { setLoading(false); setRefreshing(false); });
  };

  useEffect(() => { fetchData(false); }, []);

  const refresh = () => {
    setRefreshing(true);
    fetchData(true);
  };

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-700/60 p-4 animate-pulse">
        <div className="h-4 bg-gray-800 rounded w-32 mb-3" />
        <div className="h-8 bg-gray-800 rounded w-20 mb-2" />
        <div className="h-3 bg-gray-800 rounded w-full" />
      </div>
    );
  }

  if (!data || data.score === null) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-700/60 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Activity size={14} className="text-yellow-400" />
          <span className="text-sm font-semibold text-gray-300">CNN Fear & Greed</span>
        </div>
        <p className="text-xs text-gray-500">{data?.error ?? "데이터 없음 — 파이프라인 실행 후 갱신됩니다"}</p>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="mt-2 min-h-[44px] flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50"
        >
          <RefreshCw size={11} className={refreshing ? "animate-spin" : ""} />
          지금 가져오기
        </button>
      </div>
    );
  }

  const ratingKey = data.rating_en ?? "neutral";
  const colorClass = RATING_COLOR[ratingKey] ?? "text-yellow-400";
  const bgClass = RATING_BG[ratingKey] ?? "bg-yellow-500/20 border-yellow-500/30";

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700/60 p-4 space-y-3">
      {/* 헤더 */}
      <div className="flex items-center gap-2">
        <Activity size={14} className="text-yellow-400" />
        <span className="text-sm font-semibold text-gray-300">CNN Fear & Greed</span>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="ml-auto -my-3 -mr-3 min-w-[44px] min-h-[44px] flex items-center justify-center text-gray-600 hover:text-gray-400 disabled:opacity-50"
          title="새로고침"
        >
          <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} />
        </button>
      </div>

      {/* 점수 + 등급 */}
      <div className="flex items-end gap-3">
        <div className={`text-4xl font-bold ${colorClass}`}>{data.score}</div>
        <div className={`px-2 py-0.5 rounded border text-xs font-semibold mb-1 ${bgClass} ${colorClass}`}>
          {data.rating_kr ?? RATING_LABEL[ratingKey] ?? ratingKey}
        </div>
      </div>

      {/* 게이지 */}
      <ScoreGauge score={data.score} />

      {/* 기간별 비교 */}
      <div className="space-y-1.5 pt-1 border-t border-gray-800">
        <MiniBar label="전일 대비" value={data.score} prevValue={data.previous_close} />
        <MiniBar label="1주일 전" value={data.previous_1_week} prevValue={null} />
        <MiniBar label="1개월 전" value={data.previous_1_month} prevValue={null} />
        <MiniBar label="1년 전" value={data.previous_1_year} prevValue={null} />
      </div>

      {/* 출처 + 업데이트 시각 */}
      <div className="text-[10px] text-gray-600 pt-1 border-t border-gray-800">
        출처: CNN Markets · {data.fetched_at ? new Date(data.fetched_at).toLocaleString("ko-KR") : "—"}
      </div>
    </div>
  );
}
