"use client";

import { useState } from "react";
import { Predictions, Article, api } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

type Props = {
  predictions: Predictions;
  markets?: string[]; // 표시할 시장만 필터링. 미지정 시 전체 표시
};

const MARKET_LABELS: Record<string, string> = {
  kospi: "KOSPI",
  usd_krw: "USD/KRW",
  samsung: "삼성전자",
  hynix: "SK하이닉스",
  nasdaq: "NASDAQ",
  sp500: "S&P500",
  dow: "다우존스",
  nvidia: "NVIDIA",
};

const MARKET_UNITS: Record<string, string> = {
  kospi: "pt",
  usd_krw: "₩",
  samsung: "₩",
  hynix: "₩",
  nasdaq: "pt",
  sp500: "pt",
  dow: "pt",
  nvidia: "$",
};

// market card key → API market param mapping
const MARKET_PARAM: Record<string, string> = {
  kospi: "kospi",
  usd_krw: "usd_krw",
  samsung: "samsung",
  hynix: "hynix",
  nasdaq: "nasdaq",
  sp500: "sp500",
  dow: "dow",
  nvidia: "nvidia",
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: "text-green-400",
  negative: "text-red-400",
  neutral: "text-gray-400",
  cautious: "text-yellow-400",
};

function formatNum(val: number, key: string): string {
  if (key === "usd_krw") return val.toFixed(2);
  if (key === "samsung" || key === "hynix") return (val / 1000).toFixed(0) + "K";
  if (key === "nvidia") return val.toFixed(2);
  return val.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

function RelatedArticles({ marketKey }: { marketKey: string }) {
  const [articles, setArticles] = useState<Article[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const marketParam = MARKET_PARAM[marketKey];

  if (!marketParam) return null;

  const load = () => {
    if (articles !== null || loading) return;
    setLoading(true);
    api
      .relatedArticles(marketParam)
      .then((res) => setArticles(res.articles))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  return (
    <div className="mt-2 pt-2 border-t border-gray-800">
      {articles === null && !loading && !error && (
        <button
          onClick={load}
          className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
        >
          관련 기사 보기
          <ChevronDown size={11} />
        </button>
      )}
      {loading && (
        <p className="text-xs text-gray-600">관련 기사 로딩 중...</p>
      )}
      {error && (
        <p className="text-xs text-red-400">불러오기 실패</p>
      )}
      {articles !== null && articles.length === 0 && (
        <p className="text-xs text-gray-600">관련 기사 없음</p>
      )}
      {articles !== null && articles.length > 0 && (
        <div className="space-y-1.5 mt-1">
          {articles.map((a, i) => (
            <a
              key={i}
              href={a.link || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="block group"
            >
              <div className="flex items-start gap-1.5">
                <span className={`text-xs mt-0.5 flex-shrink-0 ${SENTIMENT_COLORS[a.sentiment] ?? "text-gray-400"}`}>
                  ●
                </span>
                <span className="text-xs text-gray-400 group-hover:text-gray-200 transition-colors line-clamp-2 flex-1">
                  {a.title}
                </span>
                {a.link && (
                  <ExternalLink size={10} className="text-gray-600 group-hover:text-gray-400 flex-shrink-0 mt-0.5" />
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MarketCards({ predictions, markets }: Props) {
  const { kronos_predictions, xgb_predictions, fused_analysis } = predictions;
  const [expandedRelated, setExpandedRelated] = useState<string | null>(null);

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-400">시장 예측 (Kronos + XGBoost + AI 융합)</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(kronos_predictions).filter(([key]) => !markets || markets.includes(key)).map(([key, pred]) => {
          const isUp = pred.change_pct >= 0;
          const isBig = Math.abs(pred.change_pct) >= 3;
          const Icon = isUp ? TrendingUp : pred.change_pct === 0 ? Minus : TrendingDown;

          const fusedKey = (key === "kospi" || key === "usd_krw") ? key as "kospi" | "usd_krw" : null;
          const fused = fusedKey ? fused_analysis?.[fusedKey] : null;
          const xgb = xgb_predictions?.[key];
          const isExpanded = expandedRelated === key;

          return (
            <div
              key={key}
              className={`bg-gray-900 rounded-xl p-4 border transition-colors ${
                isBig
                  ? isUp
                    ? "border-green-500/40"
                    : "border-red-500/40"
                  : "border-gray-800"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-medium">
                  {MARKET_LABELS[key] || key.toUpperCase()}
                </span>
                <Icon
                  size={14}
                  className={isUp ? "text-green-400" : "text-red-400"}
                />
              </div>
              <div className="text-lg font-bold text-gray-100">
                {formatNum(pred.pred_close, key)}
                <span className="text-xs text-gray-500 ml-1">{MARKET_UNITS[key]}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="text-xs text-gray-500">현재 {formatNum(pred.last_close, key)}</span>
                <span
                  className={`text-xs font-semibold ml-auto ${
                    isUp ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {isUp ? "+" : ""}{pred.change_pct.toFixed(2)}%
                </span>
              </div>
              <div className="mt-2 text-xs text-gray-500">
                <span className="text-gray-600">범위 </span>
                {formatNum(pred.pred_range.low, key)} ~ {formatNum(pred.pred_range.high, key)}
              </div>
              {xgb && (
                <div className="mt-2 pt-2 border-t border-gray-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">XGBoost</span>
                    <span className={`text-xs font-semibold ${xgb.direction === "상승" ? "text-green-400" : "text-red-400"}`}>
                      {xgb.direction} {xgb.confidence}%
                    </span>
                  </div>
                </div>
              )}
              {fused && (
                <div className="mt-2 pt-2 border-t border-gray-800">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">AI 신뢰도</span>
                    <span className="text-xs text-blue-400">{fused.confidence}%</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{fused.reason}</p>
                </div>
              )}

              {/* 관련 기사 토글 */}
              {MARKET_PARAM[key] && (
                <div className="mt-2 pt-2 border-t border-gray-800">
                  <button
                    onClick={() => setExpandedRelated(isExpanded ? null : key)}
                    className="text-xs text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1 w-full"
                  >
                    관련 기사
                    {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                  </button>
                  {isExpanded && <RelatedArticles marketKey={key} />}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 핵심 섹터 */}
      {fused_analysis?.key_sector && (
        <div className="bg-gray-900 rounded-xl p-4 border border-blue-500/20">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-blue-400 font-medium">주목 섹터</span>
            <span className="text-sm font-bold text-gray-100">{fused_analysis.key_sector.name}</span>
            <span
              className={`ml-auto text-xs font-semibold ${
                fused_analysis.key_sector.direction === "강세" ? "text-green-400" : "text-red-400"
              }`}
            >
              {fused_analysis.key_sector.direction}
            </span>
          </div>
          <p className="text-xs text-gray-400">{fused_analysis.key_sector.reason}</p>
        </div>
      )}
    </div>
  );
}
