"use client";

import { useEffect, useState } from "react";
import {
  ComposedChart,
  Bar,
  Cell,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { api, PredictionRecord } from "@/lib/api";

const MARKET_GROUPS = [
  {
    group: "국장",
    markets: [
      { key: "kospi", label: "코스피", pred: "kospi_pred_dir", actual: "kospi_actual_change" },
      { key: "usdkrw", label: "달러/원", pred: "usdkrw_pred_dir", actual: "usdkrw_actual_change" },
      { key: "samsung", label: "삼성전자", pred: "samsung_pred_dir", actual: "samsung_actual_change" },
      { key: "skhynix", label: "SK하이닉스", pred: "skhynix_pred_dir", actual: "skhynix_actual_change" },
    ],
  },
  {
    group: "미장",
    markets: [
      { key: "nasdaq", label: "나스닥", pred: "nasdaq_pred_dir", actual: "nasdaq_actual_change" },
      { key: "sp500", label: "S&P500", pred: "sp500_pred_dir", actual: "sp500_actual_change" },
      { key: "dow", label: "DOW", pred: "dow_pred_dir", actual: "dow_actual_change" },
      { key: "nvidia", label: "NVIDIA", pred: "nvidia_pred_dir", actual: "nvidia_actual_change" },
    ],
  },
] as const;

type Market = (typeof MARKET_GROUPS)[number]["markets"][number];

function isHit(record: PredictionRecord, market: Market): boolean | null {
  const pred = record[market.pred as keyof PredictionRecord] as string | null;
  const actual = record[market.actual as keyof PredictionRecord] as number | null;
  if (!pred || actual === null) return null;
  const actualDir = actual > 0 ? "상승" : "하락";
  return pred === actualDir;
}

function formatDay(day: string) {
  const d = new Date(day + "T00:00:00");
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs shadow-xl min-w-[160px]">
      <p className="text-gray-400 mb-2 font-medium">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="text-gray-200 font-medium">
            {p.value !== null && p.value !== undefined
              ? typeof p.value === "number"
                ? `${p.value > 0 ? "+" : ""}${p.value.toFixed(1)}%`
                : p.value
              : "-"}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function PredictionHistoryChart() {
  const [records, setRecords] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeGroup, setActiveGroup] = useState<"국장" | "미장">("국장");
  const [selectedMarket, setSelectedMarket] = useState<Market>(
    MARKET_GROUPS[0].markets[0]
  );

  useEffect(() => {
    api
      .predictionsHistory()
      .then((res) => setRecords(res.records))
      .finally(() => setLoading(false));
  }, []);

  const verified = records.filter((r) => r.verified_at);

  if (loading) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-gray-500 text-sm">
        로딩 중...
      </div>
    );
  }

  if (verified.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-gray-500 text-sm">
        아직 검증된 예측 데이터가 없습니다. 파이프라인이 2회 이상 실행되면 표시됩니다.
      </div>
    );
  }

  const chartData = verified.map((r) => ({
    day: formatDay(r.day),
    actualChange: r[selectedMarket.actual as keyof PredictionRecord] as number | null,
    cumulativeAccuracy: r.cumulative_accuracy,
    hit: isHit(r, selectedMarket),
    pred: r[selectedMarket.pred as keyof PredictionRecord] as string | null,
  }));

  const totalHits = verified.reduce((s, r) => s + (r.direction_hits ?? 0), 0);
  const totalPreds = verified.reduce((s, r) => s + (r.direction_total ?? 0), 0);
  const overallAccuracy = totalPreds > 0 ? Math.round((totalHits / totalPreds) * 100) : 0;

  const currentGroupMarkets = MARKET_GROUPS.find((g) => g.group === activeGroup)!.markets;

  const marketStats = currentGroupMarkets.map((m) => {
    let hits = 0, total = 0;
    verified.forEach((r) => {
      const h = isHit(r, m);
      if (h !== null) { total++; if (h) hits++; }
    });
    return { ...m, hits, total, accuracy: total > 0 ? Math.round((hits / total) * 100) : null };
  });

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 space-y-0">
      {/* 헤더 */}
      <div className="px-5 pt-5 pb-4 border-b border-gray-800">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-200">예측 적중률 히스토리</h3>
            <p className="text-xs text-gray-500 mt-0.5">AI 시장 방향 예측 vs 실제 결과</p>
          </div>
          <div className="text-right">
            <div
              className={`text-2xl font-bold ${
                overallAccuracy >= 60
                  ? "text-green-400"
                  : overallAccuracy >= 50
                  ? "text-yellow-400"
                  : "text-red-400"
              }`}
            >
              {overallAccuracy}%
            </div>
            <div className="text-xs text-gray-500">
              {verified.length}일 · {totalHits}/{totalPreds}건 적중
            </div>
          </div>
        </div>

        {/* 국장/미장 그룹 탭 */}
        <div className="flex items-center gap-2 mt-4">
          <div className="flex gap-1 bg-gray-800 rounded-lg p-0.5">
            {MARKET_GROUPS.map((g) => (
              <button
                key={g.group}
                onClick={() => {
                  setActiveGroup(g.group as "국장" | "미장");
                  setSelectedMarket(g.markets[0]);
                }}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                  activeGroup === g.group
                    ? "bg-gray-600 text-white"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                {g.group}
              </button>
            ))}
          </div>
        </div>

        {/* 마켓별 미니 통계 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 mt-3">
          {marketStats.map((m) => (
            <button
              key={m.key}
              onClick={() => setSelectedMarket(currentGroupMarkets.find((x) => x.key === m.key)!)}
              className={`rounded-lg p-2.5 text-left transition-colors border ${
                selectedMarket.key === m.key
                  ? "bg-blue-900/40 border-blue-700"
                  : "bg-gray-800 border-gray-700 hover:bg-gray-700"
              }`}
            >
              <div className="text-xs text-gray-400">{m.label}</div>
              <div
                className={`text-lg font-bold mt-0.5 ${
                  m.accuracy === null
                    ? "text-gray-600"
                    : m.accuracy >= 60
                    ? "text-green-400"
                    : m.accuracy >= 50
                    ? "text-yellow-400"
                    : "text-red-400"
                }`}
              >
                {m.accuracy !== null ? `${m.accuracy}%` : "-"}
              </div>
              <div className="text-xs text-gray-600">{m.hits}/{m.total}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 차트 */}
      <div className="px-5 pt-5 pb-4">
        <p className="text-xs text-gray-500 mb-3">
          <span className="text-gray-300 font-medium">{selectedMarket.label}</span> — 실제 등락률(막대) &amp; 누적 적중률(선)
        </p>
        <ResponsiveContainer width="100%" height={240}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="day" tick={{ fill: "#6b7280", fontSize: 11 }} />
            <YAxis
              yAxisId="left"
              tick={{ fill: "#6b7280", fontSize: 11 }}
              tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              tick={{ fill: "#6b7280", fontSize: 11 }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "11px", color: "#9ca3af" }} />
            <ReferenceLine yAxisId="left" y={0} stroke="#4b5563" />
            <Bar
              yAxisId="left"
              dataKey="actualChange"
              name="실제 등락률"
              radius={[2, 2, 0, 0]}
              label={false}
            >
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    entry.hit === null ? "#4b5563" : entry.hit ? "#22c55e" : "#ef4444"
                  }
                />
              ))}
            </Bar>
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cumulativeAccuracy"
              name="누적 적중률"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              strokeDasharray="4 2"
            />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="flex gap-4 mt-2 text-xs text-gray-500">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-green-500 inline-block" />예측 적중
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-red-500 inline-block" />예측 빗나감
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-gray-600 inline-block" />미검증
          </span>
        </div>
      </div>
    </div>
  );
}
