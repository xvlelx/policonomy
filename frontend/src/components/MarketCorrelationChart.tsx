"use client";

import { useEffect, useState } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { api, MarketCorrelationPoint } from "@/lib/api";

type MarketKey = keyof Pick<
  MarketCorrelationPoint,
  | "kospi_change"
  | "usdkrw_change"
  | "samsung_change"
  | "skhynix_change"
  | "nasdaq_change"
  | "sp500_change"
  | "dow_change"
  | "nvidia_change"
>;

const MARKET_GROUPS = [
  {
    group: "국장",
    markets: [
      { key: "kospi_change" as MarketKey, label: "KOSPI" },
      { key: "usdkrw_change" as MarketKey, label: "달러/원" },
      { key: "samsung_change" as MarketKey, label: "삼성전자" },
      { key: "skhynix_change" as MarketKey, label: "SK하이닉스" },
    ],
  },
  {
    group: "미장",
    markets: [
      { key: "nasdaq_change" as MarketKey, label: "나스닥" },
      { key: "sp500_change" as MarketKey, label: "S&P500" },
      { key: "dow_change" as MarketKey, label: "DOW" },
      { key: "nvidia_change" as MarketKey, label: "NVIDIA" },
    ],
  },
];

const ALL_MARKETS = MARKET_GROUPS.flatMap((g) => g.markets);

const DAY_OPTIONS = [14, 30, 60];

type TooltipPayloadItem = {
  dataKey?: string | number;
  name?: string;
  value?: number | string | null;
  color?: string;
};

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs shadow-xl min-w-[180px]">
      <p className="text-gray-400 mb-2 font-medium">{label}</p>
      {payload.map((p) => (
        <div key={p.dataKey} className="flex justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="text-gray-200 font-medium">
            {p.value !== null && p.value !== undefined
              ? typeof p.value === "number"
                ? `${p.value > 0 ? "+" : ""}${p.value.toFixed(2)}${(p.name ?? "").includes("감성") ? "" : "%"}`
                : p.value
              : "-"}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function MarketCorrelationChart() {
  const [selectedMarket, setSelectedMarket] = useState(ALL_MARKETS[0]);
  const [activeGroup, setActiveGroup] = useState("국장");
  const [days, setDays] = useState(30);
  // 응답에 요청 기간(days)을 함께 저장해 로딩 여부를 파생 (effect 내 동기 setState 회피)
  const [result, setResult] = useState<{ days: number; data: MarketCorrelationPoint[] | null } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .marketCorrelation(days)
      .then((res) => { if (!cancelled) setResult({ days, data: res.data }); })
      .catch(() => { if (!cancelled) setResult({ days, data: null }); });
    return () => { cancelled = true; };
  }, [days]);

  const loading = result?.days !== days;
  const failed = !loading && result?.data == null;
  const data: MarketCorrelationPoint[] = !loading && result?.data ? result.data : [];

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-gray-500 text-sm">
        로딩 중...
      </div>
    );
  }

  if (failed) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-red-400 text-sm">
        상관관계 데이터를 불러오지 못했습니다.
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-gray-500 text-sm">
        아직 상관관계 데이터가 없습니다. 파이프라인이 2일 이상 실행된 후 표시됩니다.
      </div>
    );
  }

  const chartData = data.map((d) => ({
    day: d.day.slice(5),
    sentiment: d.combined_sentiment !== null ? +(d.combined_sentiment * 100).toFixed(1) : null,
    market: d[selectedMarket.key] !== null ? +(d[selectedMarket.key] as number).toFixed(2) : null,
  }));

  const pairs = chartData.filter((d) => d.sentiment !== null && d.market !== null);
  let correlation: number | null = null;
  if (pairs.length >= 3) {
    const n = pairs.length;
    const avgS = pairs.reduce((s, d) => s + d.sentiment!, 0) / n;
    const avgM = pairs.reduce((s, d) => s + d.market!, 0) / n;
    const num = pairs.reduce((s, d) => s + (d.sentiment! - avgS) * (d.market! - avgM), 0);
    const denS = Math.sqrt(pairs.reduce((s, d) => s + (d.sentiment! - avgS) ** 2, 0));
    const denM = Math.sqrt(pairs.reduce((s, d) => s + (d.market! - avgM) ** 2, 0));
    correlation = denS * denM > 0 ? +(num / (denS * denM)).toFixed(2) : null;
  }

  const corrColor =
    correlation === null
      ? "text-gray-500"
      : Math.abs(correlation) >= 0.5
      ? "text-green-400"
      : Math.abs(correlation) >= 0.3
      ? "text-yellow-400"
      : "text-gray-400";

  const currentGroupMarkets =
    MARKET_GROUPS.find((g) => g.group === activeGroup)?.markets ?? [];

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 space-y-0">
      <div className="px-5 pt-5 pb-4 border-b border-gray-800">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-200">뉴스 감성 × 시장 상관관계</h3>
            <p className="text-xs text-gray-500 mt-0.5">종합 뉴스 감성 점수 vs 실제 시장 등락률</p>
          </div>
          {correlation !== null && (
            <div className="text-right">
              <div className={`text-2xl font-bold ${corrColor}`}>
                {correlation > 0 ? "+" : ""}
                {correlation}
              </div>
              <div className="text-xs text-gray-500">상관계수 r</div>
            </div>
          )}
        </div>

        {/* 컨트롤 */}
        <div className="flex gap-2 mt-3 flex-wrap items-center">
          {/* 국장/미장 그룹 탭 */}
          <div className="flex gap-1 bg-gray-800 rounded-lg p-0.5">
            {MARKET_GROUPS.map((g) => (
              <button
                key={g.group}
                onClick={() => {
                  setActiveGroup(g.group);
                  setSelectedMarket(g.markets[0]);
                }}
                className={`px-3 py-1 min-h-[44px] rounded-md text-xs font-semibold transition-colors ${
                  activeGroup === g.group
                    ? "bg-gray-600 text-white"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {g.group}
              </button>
            ))}
          </div>

          {/* 마켓 탭 */}
          <div className="flex flex-wrap gap-1">
            {currentGroupMarkets.map((m) => (
              <button
                key={m.key}
                onClick={() => setSelectedMarket(m)}
                className={`px-2.5 py-1 min-h-[44px] rounded text-xs font-medium transition-colors ${
                  selectedMarket.key === m.key
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* 기간 */}
          <div className="flex gap-1 ml-auto">
            {DAY_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-2.5 py-1 min-h-[44px] rounded text-xs font-medium transition-colors ${
                  days === d
                    ? "bg-gray-600 text-white"
                    : "bg-gray-800 text-gray-500 hover:bg-gray-700"
                }`}
              >
                {d}일
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="px-5 pt-4 pb-5">
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="day"
              tick={{ fill: "#6b7280", fontSize: 10 }}
              interval={Math.floor(chartData.length / 6)}
              minTickGap={16}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: "#6b7280", fontSize: 10 }}
              tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[-100, 100]}
              tick={{ fill: "#6b7280", fontSize: 10 }}
              tickFormatter={(v) => `${v > 0 ? "+" : ""}${v}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", color: "#9ca3af" }} />
            <ReferenceLine yAxisId="left" y={0} stroke="#4b5563" />
            <ReferenceLine yAxisId="right" y={0} stroke="#4b5563" strokeDasharray="3 3" />
            <Bar
              yAxisId="left"
              dataKey="market"
              name={`${selectedMarket.label} 등락률`}
              fill="#3b82f6"
              opacity={0.7}
              radius={[2, 2, 0, 0]}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="sentiment"
              name="종합 감성 점수"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              strokeDasharray="4 2"
            />
          </ComposedChart>
        </ResponsiveContainer>
        <p className="text-xs text-gray-600 mt-2">
          감성 점수: (긍정-부정)/전체 × 100 | 상관계수 |r| ≥ 0.5: 강한 상관
        </p>
      </div>
    </div>
  );
}
