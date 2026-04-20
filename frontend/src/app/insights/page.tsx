"use client";

import { useEffect, useState } from "react";
import { api, WeeklyInsight } from "@/lib/api";
import { TrendingUp } from "lucide-react";
import Link from "next/link";
import WeeklyTopArticles from "@/components/WeeklyTopArticles";
import PredictionHistoryChart from "@/components/PredictionHistoryChart";
import MarketCorrelationChart from "@/components/MarketCorrelationChart";

function SentimentBar({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-600 text-xs">-</span>;
  const pct = Math.round(Math.abs(value) * 100);
  const isPos = value > 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full ${isPos ? "bg-green-500" : "bg-red-500"}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span className={`text-xs w-10 text-right ${isPos ? "text-green-400" : "text-red-400"}`}>
        {isPos ? "+" : ""}{(value * 100).toFixed(0)}%
      </span>
    </div>
  );
}

function ChangeChip({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-600 text-xs">-</span>;
  const isPos = value > 0;
  return (
    <span className={`text-xs font-medium ${isPos ? "text-green-400" : "text-red-400"}`}>
      {isPos ? "▲" : "▼"} {Math.abs(value).toFixed(2)}%
    </span>
  );
}

function AccuracyBadge({ accuracy }: { accuracy: number | null }) {
  if (accuracy === null) return null;
  const color =
    accuracy >= 70 ? "text-green-400 bg-green-900/30 border-green-800" :
    accuracy >= 50 ? "text-yellow-400 bg-yellow-900/30 border-yellow-800" :
    "text-red-400 bg-red-900/30 border-red-800";
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-bold ${color}`}>
      {accuracy.toFixed(1)}%
    </span>
  );
}

const CAT_LABELS: { key: keyof WeeklyInsight; label: string }[] = [
  { key: "avg_politics_sentiment", label: "정치·경제" },
  { key: "avg_global_sentiment", label: "글로벌" },
  { key: "avg_tech_sentiment", label: "테크" },
  { key: "avg_realestate_sentiment", label: "부동산" },
];

export default function InsightsPage() {
  const [weeks, setWeeks] = useState<WeeklyInsight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.weeklyInsights()
      .then((res) => setWeeks(res.weeks))
      .catch(() => setError("인사이트 데이터를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">주간 인사이트 아카이브</h1>
          <p className="text-xs text-gray-400 mt-1">일별 데이터 주간 집계 — 뉴스 감성 vs 실제 시장 결과</p>
        </div>
        <Link
          href="/"
          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-300 hover:bg-gray-700 transition-colors"
        >
          ← 대시보드
        </Link>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <div className="text-gray-400 text-sm">인사이트 불러오는 중...</div>
        </div>
      )}
      {error && (
        <div className="py-20 text-center text-red-400">{error}</div>
      )}

      {!loading && !error && weeks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
          <TrendingUp size={32} className="text-gray-600" />
          <p className="text-gray-300 font-medium">아직 데이터가 없습니다</p>
          <p className="text-sm text-gray-400 mt-1">파이프라인이 매일 23:30에 실행되어 데이터를 쌓습니다.</p>
        </div>
      )}

      {/* 예측 적중률 히스토리 */}
      <PredictionHistoryChart />

      {/* 뉴스 감성 × 시장 상관관계 */}
      <MarketCorrelationChart />

      {/* 주간 TOP 10 뉴스 */}
      <WeeklyTopArticles />

      {/* 주간 카드 목록 */}
      {weeks.map((w) => (
        <div
          key={w.week_label}
          className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden"
        >
          {/* 카드 헤더 */}
          <div className="flex items-center justify-between px-5 py-3 bg-gray-800/50 border-b border-gray-800">
            <div>
              <span className="text-sm font-semibold text-gray-200">
                {w.week_start} ~ {w.week_end}
              </span>
              <span className="ml-2 text-xs text-gray-400">
                ({w.days_count}일 데이터, 기사 {w.total_articles}건)
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400">예측 적중률</span>
              <AccuracyBadge accuracy={w.accuracy} />
            </div>
          </div>

          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 카테고리별 감성 */}
            <div>
              <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">
                카테고리별 평균 감성
              </h4>
              <div className="space-y-2.5">
                {CAT_LABELS.map(({ key, label }) => (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-xs text-gray-400 w-16 flex-shrink-0">{label}</span>
                    <div className="flex-1">
                      <SentimentBar value={w[key] as number | null} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 실제 시장 결과 */}
            <div>
              <h4 className="text-xs font-semibold text-gray-400 mb-3 uppercase tracking-wide">
                실제 시장 결과 (주간 평균)
              </h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-gray-800">
                  <span className="text-sm text-gray-400">코스피</span>
                  <ChangeChip value={w.avg_kospi_change} />
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-800">
                  <span className="text-sm text-gray-400">나스닥</span>
                  <ChangeChip value={w.avg_nasdaq_change} />
                </div>
                {w.total_preds > 0 && (
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs text-gray-400">검증된 예측</span>
                    <span className="text-xs text-gray-300">
                      {w.total_hits}/{w.total_preds}건 적중
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
