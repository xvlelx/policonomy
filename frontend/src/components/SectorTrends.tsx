"use client";

import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { api, SectorTrend } from "@/lib/api";

function Arrow({ direction }: { direction: SectorTrend["direction"] }) {
  if (direction === "up") return <TrendingUp size={16} className="text-green-400" />;
  if (direction === "down") return <TrendingDown size={16} className="text-red-400" />;
  return <Minus size={16} className="text-gray-500" />;
}

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <div className="h-1.5 bg-gray-800 rounded-full" />;
  const pct = Math.min(100, Math.abs(score) * 100);
  const isPos = score >= 0;
  return (
    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full ${isPos ? "bg-green-500" : "bg-red-500"}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function SectorTrends() {
  const [trends, setTrends] = useState<SectorTrend[]>([]);
  const [hasData, setHasData] = useState(false);
  const [loading, setLoading] = useState(true);
  const [recentDays, setRecentDays] = useState<number | undefined>();
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .sectorTrends()
      .then((res) => {
        setTrends(res.trends);
        setHasData(res.has_data);
        setRecentDays(res.recent_days);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center text-gray-500 text-xs">
        섹터 트렌드 로딩 중...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center text-red-400 text-xs">
        섹터 트렌드를 불러오지 못했습니다.
      </div>
    );
  }

  if (!hasData || trends.length === 0) {
    return null;
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-300">섹터 트렌드</h3>
        <span className="text-xs text-gray-600">최근 {recentDays ?? 7}일 vs 이전 7일</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
        {trends.map((t) => {
          const isUp = t.direction === "up";
          const isDown = t.direction === "down";
          const scoreColor =
            t.recent_score === null ? "text-gray-600"
            : t.recent_score > 0.1 ? "text-green-400"
            : t.recent_score < -0.1 ? "text-red-400"
            : "text-gray-400";

          return (
            <div
              key={t.key}
              className={`rounded-lg p-3 border ${
                isUp ? "border-green-800/50 bg-green-900/10"
                : isDown ? "border-red-800/50 bg-red-900/10"
                : "border-gray-800 bg-gray-800/30"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">{t.label}</span>
                <Arrow direction={t.direction} />
              </div>
              <ScoreBar score={t.recent_score} />
              <div className="flex items-center justify-between mt-2">
                <span className={`text-sm font-bold ${scoreColor}`}>
                  {t.recent_score !== null
                    ? `${t.recent_score > 0 ? "+" : ""}${(t.recent_score * 100).toFixed(0)}%`
                    : "-"}
                </span>
                {t.delta !== null && (
                  <span className={`text-xs ${isUp ? "text-green-500" : isDown ? "text-red-500" : "text-gray-600"}`}>
                    {t.delta > 0 ? "+" : ""}{(t.delta * 100).toFixed(0)}pt
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
