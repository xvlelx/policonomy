"use client";

import { NewsImpactItem, Predictions } from "@/lib/api";

const MARKET_LABELS: Record<string, string> = {
  kospi: "KOSPI",
  usd_krw: "USD/KRW",
  samsung: "삼성전자",
  nasdaq: "NASDAQ",
};

type Props = {
  impact: NewsImpactItem[];
  predictions: Predictions;
};

function SentimentBar({ netScore }: { netScore: number }) {
  const pct = Math.abs(netScore) * 100;
  const isPos = netScore >= 0;
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden relative">
        {isPos ? (
          <div
            className="absolute left-0 top-0 h-full bg-green-500 rounded-full"
            style={{ width: `${pct}%` }}
          />
        ) : (
          <div
            className="absolute right-0 top-0 h-full bg-red-500 rounded-full"
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      <span
        className={`text-xs font-semibold tabular-nums ${
          isPos ? "text-green-400" : netScore < -0.1 ? "text-red-400" : "text-gray-400"
        }`}
      >
        {isPos ? "+" : ""}{Math.round(netScore * 100)}%
      </span>
    </div>
  );
}

function MarketBadge({
  market,
  predictions,
}: {
  market: string;
  predictions: Predictions;
}) {
  const xgb = predictions.xgb_predictions?.[market === "usd_krw" ? "usdkrw" : market === "samsung" ? "samsung" : market];
  const kronos = predictions.kronos_predictions?.[market];
  const direction = xgb?.direction ?? kronos?.direction ?? null;
  const confidence = xgb?.confidence ?? null;
  const isUp = direction === "상승";

  return (
    <div
      className={`flex items-center gap-1 px-2 py-1 rounded-lg border text-xs ${
        direction === "상승"
          ? "bg-green-950/40 border-green-500/30 text-green-300"
          : direction === "하락"
          ? "bg-red-950/40 border-red-500/30 text-red-300"
          : "bg-gray-800 border-gray-700 text-gray-400"
      }`}
    >
      <span>{MARKET_LABELS[market] ?? market.toUpperCase()}</span>
      {direction && (
        <span className="font-semibold">
          {isUp ? "▲" : "▼"} {direction}
          {confidence !== null && (
            <span className="opacity-70 ml-0.5">{confidence}%</span>
          )}
        </span>
      )}
    </div>
  );
}

export default function NewsImpactFlow({ impact, predictions }: Props) {
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-400">뉴스 → 시장 영향 흐름</h2>
      <div className="bg-gray-900 rounded-xl border border-gray-800 divide-y divide-gray-800">
        {impact.map((item) => (
          <div key={item.category} className="p-4 flex flex-col md:flex-row md:items-center gap-3">
            {/* 뉴스 카테고리 */}
            <div className="w-full md:w-40 flex-shrink-0">
              <div className="text-sm font-medium text-gray-200">{item.label}</div>
              <div className="text-xs text-gray-500 mt-0.5">
                <span className="text-green-400">+{item.positive}</span>
                {" / "}
                <span className="text-red-400">-{item.negative}</span>
                {item.neutral > 0 && (
                  <span className="text-gray-600"> / ~{item.neutral}</span>
                )}
                <span className="ml-1 text-gray-600">({item.total}건)</span>
              </div>
            </div>

            {/* 감성 바 */}
            <div className="flex-shrink-0">
              <SentimentBar netScore={item.net_score} />
            </div>

            {/* 화살표 */}
            <div className="hidden md:block text-gray-600 flex-shrink-0">→</div>

            {/* 영향 시장 + 예측 */}
            <div className="flex flex-wrap gap-1.5">
              {item.markets.map((market) => (
                <MarketBadge key={market} market={market} predictions={predictions} />
              ))}
            </div>

            {/* 해석 텍스트 */}
            <div className="text-xs text-gray-500 md:ml-auto md:text-right max-w-xs">
              {item.net_score <= -0.4
                ? "강한 부정 → 하락 압력"
                : item.net_score <= -0.1
                ? "부정 우세 → 약세 경향"
                : item.net_score >= 0.4
                ? "강한 긍정 → 상승 기대"
                : item.net_score >= 0.1
                ? "긍정 우세 → 강세 경향"
                : "혼조세 → 영향 제한적"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
