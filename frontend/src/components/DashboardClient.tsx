"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api, Summary, Predictions, ArticleStats } from "@/lib/api";
import Link from "next/link";
import { ChevronRight, ChevronDown, ChevronUp } from "lucide-react";
import PipelineStatus from "./PipelineStatus";
import WeeklySummary from "./WeeklySummary";
import UrgentNewsBanner from "./UrgentNewsBanner";
import SentimentChart from "./SentimentChart";
import DashboardTabs from "./DashboardTabs";
import KospiTab from "./KospiTab";
import UsMarketTab from "./UsMarketTab";
import UnofficialIndicatorsTab from "./UnofficialIndicatorsTab";
import SettingsSlideOver from "./SettingsSlideOver";

type Tab = "kospi" | "us" | "unofficial";
const TAB_ORDER: Tab[] = ["kospi", "us", "unofficial"];

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-4">
      {children}
    </p>
  );
}


export default function DashboardClient() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [predictions, setPredictions] = useState<Predictions | null>(null);
  const [articleStats, setArticleStats] = useState<ArticleStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("kospi");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [statsVisible, setStatsVisible] = useState(false);

  const prevStatusRef = useRef<string>("unknown");
  const touchStartXRef = useRef<number>(0);

  const fetchAll = useCallback(async () => {
    try {
      const [s, preds, stats] = await Promise.all([
        api.summary(),
        api.predictions(),
        api.articleStats(),
      ]);
      setSummary(s);
      setPredictions(preds?.kronos_predictions ? preds : null);
      setArticleStats(stats);
      prevStatusRef.current = s.pipeline.status;
      setError(null);
    } catch {
      setError("백엔드 서버에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(async () => {
      try {
        const s = await api.summary();
        setSummary(s);
        if (prevStatusRef.current === "running" && s.pipeline.status === "completed") {
          fetchAll();
        }
        prevStatusRef.current = s.pipeline.status;
      } catch {}
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-400 text-lg">Policonomy 로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-red-400 text-lg">{error}</div>
        <button
          onClick={fetchAll}
          className="px-4 py-2 min-h-[44px] bg-blue-600 rounded-lg hover:bg-blue-700 text-sm"
        >
          재시도
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4">

      {/* ── 1. 헤더 ── */}
      <header className="flex flex-wrap items-center justify-between gap-3 py-5 border-b border-gray-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-blue-400">Poli</span>conomy
          </h1>
          <p className="text-gray-400 text-xs mt-0.5">AI 정치·경제 분석 & 예측</p>
        </div>
        <nav className="flex items-center gap-2">
          <Link
            href="/reports"
            className="px-3 py-2 min-h-[44px] flex items-center rounded-lg text-xs font-medium text-blue-300 bg-blue-900/40 border border-blue-800 hover:bg-blue-800/60 transition-colors"
          >
            브리핑
          </Link>
          <Link
            href="/insights"
            className="px-3 py-2 min-h-[44px] flex items-center rounded-lg text-xs font-medium text-gray-400 bg-gray-800/60 border border-gray-700 hover:bg-gray-700 transition-colors"
          >
            트렌드 분석
          </Link>
          <Link
            href="/newsletter"
            className="px-3 py-2 min-h-[44px] flex items-center rounded-lg text-xs font-medium text-gray-400 bg-gray-800/60 border border-gray-700 hover:bg-gray-700 transition-colors"
          >
            뉴스레터
          </Link>
          <button
            onClick={() => setSettingsOpen(true)}
            className="px-3 py-2 min-h-[44px] flex items-center rounded-lg text-xs font-medium text-gray-500 hover:text-gray-300 transition-colors"
          >
            설정
          </button>
        </nav>
      </header>

      {/* ── 2. 메타 라인 ── */}
      <div className="mt-3 flex flex-wrap items-center gap-x-3 sm:gap-x-5 gap-y-1 text-xs text-gray-400">
        {summary?.generated_at && (
          <span>
            분석 완료{" "}
            <span className="text-gray-300">
              {new Date(summary.generated_at).toLocaleString("ko-KR")}
            </span>
          </span>
        )}
        {summary?.accuracy && summary.accuracy.days > 0 && (
          <span>
            예측 적중률{" "}
            <span
              className={`font-bold ${
                summary.accuracy.direction_accuracy >= 60
                  ? "text-green-400"
                  : summary.accuracy.direction_accuracy >= 50
                  ? "text-yellow-400"
                  : "text-red-400"
              }`}
            >
              {summary.accuracy.direction_accuracy}%
            </span>
            <span className="ml-1 text-gray-400">{summary.accuracy.days}일 기준</span>
          </span>
        )}
        {articleStats && (
          <span>
            분석 기사{" "}
            <span className="text-gray-300">{articleStats.total_articles}건</span>
          </span>
        )}
      </div>

      {/* ── 3. 오늘의 요약 + 긴급 이슈 + CTA ── */}
      {summary?.weekly_summary && (
        <section className="mt-8">
          <SectionLabel>오늘의 요약</SectionLabel>
          <div className="mb-3">
            <UrgentNewsBanner />
          </div>
          <WeeklySummary
            summary={summary.weekly_summary}
            sentiment={summary.overall_sentiment}
          />
          <div className="mt-4">
            <Link
              href="/reports"
              className="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              {articleStats
                ? `전체 기사 ${articleStats.total_articles}건 보기`
                : "전체 기사 보기"}
              <ChevronRight size={14} />
            </Link>
          </div>
        </section>
      )}

      {/* ── 4. 데이터 개요 ── */}
      {articleStats && (
        <section className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <SectionLabel>데이터 개요</SectionLabel>
            <button
              className="md:hidden text-gray-500 hover:text-gray-300 transition-colors"
              onClick={() => setStatsVisible((v) => !v)}
              aria-label={statsVisible ? "접기" : "펼치기"}
            >
              {statsVisible ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
          <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${statsVisible ? "grid" : "hidden md:grid"}`}>
            <SentimentChart data={articleStats.by_sentiment} />
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-700/60">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                카테고리별 기사 수
                <span className="text-gray-400 font-normal ml-2 text-xs">
                  총 {articleStats.total_articles}건
                </span>
              </h3>
              <div className="space-y-3">
                {Object.entries(articleStats.by_category ?? {}).map(([cat, count]) => (
                  <div key={cat} className="flex items-center gap-3">
                    <div className="text-xs text-gray-400 w-20 flex-shrink-0">
                      {
                        ({
                          politics_economy: "정치·경제",
                          global_macro: "글로벌",
                          tech_industry: "테크",
                          real_estate: "부동산",
                        } as Record<string, string>)[cat] || cat
                      }
                    </div>
                    <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                      <div
                        className="bg-blue-500 h-1.5 rounded-full"
                        style={{
                          width: `${Math.min(100, (count / articleStats.total_articles) * 100)}%`,
                        }}
                      />
                    </div>
                    <div className="text-xs text-gray-300 w-6 text-right">{count}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ── 5. 시장 분석 ── */}
      <section className="mt-8">
        <SectionLabel>시장 분석</SectionLabel>
        <DashboardTabs active={activeTab} onChange={setActiveTab} />
        <div
          onTouchStart={(e) => { touchStartXRef.current = e.touches[0].clientX; }}
          onTouchEnd={(e) => {
            const dx = e.changedTouches[0].clientX - touchStartXRef.current;
            if (Math.abs(dx) < 100) return;
            const idx = TAB_ORDER.indexOf(activeTab);
            if (dx < 0 && idx < TAB_ORDER.length - 1) setActiveTab(TAB_ORDER[idx + 1]);
            if (dx > 0 && idx > 0) setActiveTab(TAB_ORDER[idx - 1]);
          }}
        >
          <div
            role="tabpanel"
            id="panel-kospi"
            aria-labelledby="tab-kospi"
            className={`mt-6 ${activeTab === "kospi" ? "" : "hidden"}`}
          >
            {predictions && <KospiTab predictions={predictions} />}
          </div>
          <div
            role="tabpanel"
            id="panel-us"
            aria-labelledby="tab-us"
            className={`mt-6 ${activeTab === "us" ? "" : "hidden"}`}
          >
            {predictions && <UsMarketTab predictions={predictions} />}
          </div>
          <div
            role="tabpanel"
            id="panel-unofficial"
            aria-labelledby="tab-unofficial"
            className={`mt-6 ${activeTab === "unofficial" ? "" : "hidden"}`}
          >
            <UnofficialIndicatorsTab />
          </div>
        </div>
      </section>

      {/* ── 6. 시스템 상태 (하단) ── */}
      {summary && (
        <section className="mt-12 pt-6 border-t border-gray-800/60">
          <SectionLabel>시스템 상태</SectionLabel>
          <PipelineStatus status={summary.pipeline} onPipelineStart={fetchAll} />
        </section>
      )}

      <div className="h-16" />

      <SettingsSlideOver open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
