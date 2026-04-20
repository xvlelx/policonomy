"use client";

import { useEffect, useState } from "react";
import { api, HedgeFundsResponse, HedgeFund } from "@/lib/api";
import { ChevronDown, ChevronUp, RefreshCw } from "lucide-react";

function fmtUSD(v: number): string {
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

function FundCard({ fund }: { fund: HedgeFund }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start justify-between p-4 text-left hover:bg-gray-800/50 transition-colors"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-100 truncate">{fund.name}</span>
            <span className="text-xs text-blue-400 bg-blue-400/10 px-1.5 py-0.5 rounded flex-shrink-0">
              {fund.quarter}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>총 {fund.total_value_fmt}</span>
            <span>{fund.holdings_count}개 종목</span>
            <span className="hidden sm:inline">공시 {fund.filed_at}</span>
          </div>
        </div>
        <div className="flex-shrink-0 ml-2 mt-0.5 text-gray-500">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-800 px-4 pb-4 pt-3">
          <p className="text-xs text-gray-500 mb-2">TOP 10 보유 종목</p>
          <div className="space-y-1.5">
            {fund.top_holdings.map((h, i) => (
              <div key={h.cusip || i} className="flex items-center gap-2">
                <span className="text-xs text-gray-600 w-4 flex-shrink-0 text-right">{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-gray-300 truncate">{h.name}</span>
                    <span className="text-xs text-gray-400 flex-shrink-0">{fmtUSD(h.value_usd)}</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2">
                    <div className="flex-1 bg-gray-800 rounded-full h-1 overflow-hidden">
                      <div
                        className="bg-blue-500 h-1 rounded-full"
                        style={{ width: `${Math.min(h.pct, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 w-10 text-right flex-shrink-0">
                      {h.pct.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function HedgeFund13F() {
  const [data, setData] = useState<HedgeFundsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const load = (force = false) => {
    if (force) setRefreshing(true);
    else setLoading(true);
    setError(false);
    api
      .hedgeFunds(force)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">헤지펀드 13F 포지션</h3>
        {data && (
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors disabled:opacity-40"
          >
            <RefreshCw size={11} className={refreshing ? "animate-spin" : ""} />
            새로고침
          </button>
        )}
      </div>

      {loading && (
        <div className="text-center py-8 text-gray-500 text-sm">SEC 13F 데이터 로딩 중...</div>
      )}

      {error && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
          <p className="text-xs text-red-400">데이터를 불러오지 못했습니다.</p>
          <button
            onClick={() => load()}
            className="mt-2 text-xs text-blue-400 hover:text-blue-300"
          >
            다시 시도
          </button>
        </div>
      )}

      {data && !loading && (
        <>
          <p className="text-xs text-gray-600">
            SEC EDGAR 13F-HR 공시 기반 · 업데이트 {new Date(data.updated_at).toLocaleString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          </p>
          <div className="space-y-2">
            {data.funds.map((fund) => (
              <FundCard key={fund.cik} fund={fund} />
            ))}
          </div>
          {data.funds.length === 0 && (
            <div className="text-center py-6 text-gray-500 text-xs">
              수집된 펀드 데이터가 없습니다. 파이프라인 실행 후 다시 확인해 주세요.
            </div>
          )}
        </>
      )}
    </div>
  );
}
