"use client";

import { useEffect, useState } from "react";
import { api, Report, ReportSession } from "@/lib/api";
import Link from "next/link";
import { ChevronDown, ChevronUp, ExternalLink, BookOpen } from "lucide-react";

const SENTIMENT_COLOR: Record<string, string> = {
  positive: "text-green-400",
  negative: "text-red-400",
  neutral: "text-gray-400",
  cautious: "text-yellow-400",
};

const REGION_BADGE: Record<string, string> = {
  KR: "bg-blue-900/40 text-blue-300",
  US: "bg-red-900/40 text-red-300",
  UK: "bg-purple-900/40 text-purple-300",
  JP: "bg-orange-900/40 text-orange-300",
  CN: "bg-yellow-900/40 text-yellow-300",
  XX: "bg-gray-800 text-gray-400",
};

const RISK_BADGE: Record<string, string> = {
  HIGH: "bg-red-900/50 text-red-300 border border-red-700/50",
  MEDIUM: "bg-yellow-900/50 text-yellow-300 border border-yellow-700/50",
  LOW: "bg-gray-800 text-gray-400 border border-gray-700",
};

const STATUS_COLOR: Record<string, string> = {
  긍정: "text-green-400",
  부정: "text-red-400",
  중립: "text-gray-400",
  불안정: "text-yellow-400",
};

// ── 섹션 헤더 ──────────────────────────────────────
function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-xs font-bold text-blue-400 bg-blue-900/30 border border-blue-700/40 px-2 py-0.5 rounded">
        {num}
      </span>
      <h2 className="text-sm font-bold text-gray-200">{title}</h2>
    </div>
  );
}

// ── ① 언론사별 헤드라인 ──────────────────────────────
function Section1({ headlines }: { headlines: Report["sections"]["headlines"] }) {
  if (!headlines.length) return <p className="text-xs text-gray-500">헤드라인 데이터 없음</p>;

  const byRegion: Record<string, typeof headlines> = {};
  headlines.forEach(h => {
    byRegion[h.region] = byRegion[h.region] || [];
    byRegion[h.region].push(h);
  });

  const regionOrder = ["KR", "US", "UK", "JP", "CN", "XX"];
  const regionLabel: Record<string, string> = {
    KR: "🇰🇷 한국", US: "🇺🇸 미국", UK: "🇬🇧 영국", JP: "🇯🇵 일본", CN: "🇨🇳 중국", XX: "기타",
  };

  return (
    <div className="space-y-4">
      {regionOrder.filter(r => byRegion[r]).map(region => (
        <div key={region}>
          <div className="text-xs font-semibold text-gray-400 mb-2">{regionLabel[region]}</div>
          <div className="space-y-2">
            {byRegion[region].map((h, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3 flex items-start gap-3">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5 ${REGION_BADGE[h.region]}`}>
                  {h.outlet}
                </span>
                <div className="flex-1 min-w-0">
                  {h.link ? (
                    <a href={h.link} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-gray-200 hover:text-white transition-colors line-clamp-2 flex items-start gap-1">
                      {h.title}
                      <ExternalLink size={10} className="flex-shrink-0 mt-0.5 text-gray-600" />
                    </a>
                  ) : (
                    <p className="text-xs text-gray-200 line-clamp-2">{h.title}</p>
                  )}
                  {h.one_line && (
                    <p className="text-xs text-gray-400 mt-1">{h.one_line}</p>
                  )}
                </div>
                <span className={`text-xs flex-shrink-0 mt-0.5 ${SENTIMENT_COLOR[h.sentiment] || "text-gray-400"}`}>●</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── ② TOP 5 이슈 ──────────────────────────────────
function Section2({ issues }: { issues: Report["sections"]["top_issues"] }) {
  const [expanded, setExpanded] = useState<number | null>(0);
  if (!issues.length) return <p className="text-xs text-gray-500">이슈 데이터 없음</p>;

  return (
    <div className="space-y-3">
      {issues.map((iss, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <button
            onClick={() => setExpanded(expanded === i ? null : i)}
            aria-expanded={expanded === i}
            className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-gray-800/50 transition-colors"
          >
            <span className="text-sm font-bold text-blue-400 flex-shrink-0">#{iss.rank}</span>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-100">{iss.title}</p>
              <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{iss.summary}</p>
            </div>
            <span className={`text-xs flex-shrink-0 mt-0.5 ${SENTIMENT_COLOR[iss.sentiment] || "text-gray-400"}`}>●</span>
            {expanded === i ? <ChevronUp size={14} className="text-gray-500 flex-shrink-0" /> : <ChevronDown size={14} className="text-gray-500 flex-shrink-0" />}
          </button>

          {expanded === i && (
            <div className="px-4 pb-4 border-t border-gray-800">
              <p className="text-xs text-gray-400 mt-3 mb-3 leading-relaxed">{iss.summary}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {[
                  { label: "🏛 정치적 의도", value: iss.political_intent },
                  { label: "💰 경제적 실리", value: iss.economic_interest },
                  { label: "🛡 안보 함의", value: iss.security_angle },
                  { label: "📈 시장 영향", value: iss.market_impact },
                  { label: "📰 언론 프레이밍", value: iss.framing },
                ].map(({ label, value }) => value ? (
                  <div key={label} className="bg-gray-800/60 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1">{label}</div>
                    <p className="text-xs text-gray-300 leading-relaxed">{value}</p>
                  </div>
                ) : null)}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── ③ 국가별 입장 ──────────────────────────────────
function Section3({ stances }: { stances: Report["sections"]["country_stances"] }) {
  if (!stances.length) return <p className="text-xs text-gray-500">국가 입장 데이터 없음</p>;

  return (
    <div className="space-y-4">
      {stances.map((s, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <p className="text-xs font-semibold text-gray-200 mb-3">{s.issue_title}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {s.countries.map((c, j) => (
              <div key={j} className="bg-gray-800/60 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-base">{c.flag}</span>
                  <span className="text-xs font-semibold text-gray-200">{c.country}</span>
                  <span className={`ml-auto text-xs px-1.5 py-0.5 rounded ${
                    c.stance_type === "지지" ? "bg-green-900/50 text-green-400" :
                    c.stance_type === "반대" ? "bg-red-900/50 text-red-400" :
                    "bg-gray-700 text-gray-400"
                  }`}>{c.stance_type}</span>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed mb-1">
                  <span className="text-gray-400">공식: </span>{c.official_position}
                </p>
                <p className="text-xs text-yellow-400/80 leading-relaxed">
                  <span className="text-gray-400">속내: </span>{c.real_intent}
                </p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── ④ 시장 데이터 ──────────────────────────────────
function Section4({ data }: { data: Report["sections"]["market_data"] }) {
  if (!data?.market_items?.length) return <p className="text-xs text-gray-500">시장 데이터 없음</p>;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {data.market_items.map((m, i) => {
          const isUp = (m.change_pct ?? 0) >= 0;
          return (
            <div key={i} className={`bg-gray-900 rounded-xl p-4 border ${
              Math.abs(m.change_pct ?? 0) >= 3
                ? isUp ? "border-green-500/30" : "border-red-500/30"
                : "border-gray-800"
            }`}>
              <div className="text-xs text-gray-400 font-medium mb-2">{m.market}</div>
              <div className="text-base font-bold text-gray-100">
                {m.pred_close?.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="text-xs text-gray-400">현재 {m.last_close?.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}</span>
                <span className={`text-xs font-semibold ml-auto ${isUp ? "text-green-400" : "text-red-400"}`}>
                  {isUp ? "+" : ""}{m.change_pct?.toFixed(2)}%
                </span>
              </div>
              {m.xgb_direction && (
                <div className="mt-2 pt-2 border-t border-gray-800 flex items-center justify-between">
                  <span className="text-xs text-gray-400">XGBoost</span>
                  <span className={`text-xs font-semibold ${m.xgb_direction === "상승" ? "text-green-400" : "text-red-400"}`}>
                    {m.xgb_direction} {m.xgb_confidence}%
                  </span>
                </div>
              )}
              {m.ai_confidence && (
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-gray-400">AI 신뢰도</span>
                  <span className="text-xs text-blue-400">{m.ai_confidence}%</span>
                </div>
              )}
              {m.ai_reason && (
                <p className="text-xs text-gray-400 mt-1 line-clamp-2">{m.ai_reason}</p>
              )}
            </div>
          );
        })}
      </div>
      {data.key_sector && (
        <div className="bg-gray-900 rounded-xl p-4 border border-blue-500/20">
          <span className="text-xs text-blue-400 font-medium">주목 섹터: </span>
          <span className="text-sm font-bold text-gray-100">{data.key_sector.name}</span>
          <span className={`ml-2 text-xs font-semibold ${data.key_sector.direction === "강세" ? "text-green-400" : "text-red-400"}`}>
            {data.key_sector.direction}
          </span>
          <p className="text-xs text-gray-400 mt-1">{data.key_sector.reason}</p>
        </div>
      )}
    </div>
  );
}

// ── ⑤ 리스크 워치리스트 ──────────────────────────────
function Section5({ watchlist }: { watchlist: Report["sections"]["risk_watchlist"] }) {
  if (!watchlist.length) return <p className="text-xs text-gray-500">리스크 데이터 없음</p>;

  return (
    <div className="space-y-3">
      {watchlist.map((item, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-start gap-3 mb-2">
            <span className={`text-xs font-bold px-2 py-0.5 rounded flex-shrink-0 ${RISK_BADGE[item.risk_level]}`}>
              {item.risk_level}
            </span>
            <p className="text-xs font-semibold text-gray-200">{item.event}</p>
            <span className={`ml-auto text-xs flex-shrink-0 ${
              item.expected_trend === "상승" ? "text-green-400" :
              item.expected_trend === "하락" ? "text-red-400" : "text-yellow-400"
            }`}>{item.expected_trend}</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed mb-2">{item.scenario}</p>
          {item.affected_markets?.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {item.affected_markets.map((m, j) => (
                <span key={j} className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded">{m}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── ⑥ Summary Matrix ──────────────────────────────
function Section6({ data }: { data: Report["sections"]["summary_matrix"] }) {
  if (!data?.matrix?.length) return <p className="text-xs text-gray-500">매트릭스 데이터 없음</p>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.matrix.map((item, i) => (
          <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-bold text-gray-200">{item.category}</span>
              <span className="text-xs text-gray-400">/ {item.category_en}</span>
              <span className={`ml-auto text-xs font-semibold ${STATUS_COLOR[item.status] || "text-gray-400"}`}>
                {item.status}
              </span>
            </div>
            <p className="text-xs text-gray-300 leading-relaxed mb-2">{item.key_trend}</p>
            <div className="space-y-1">
              <div className="flex gap-1.5">
                <span className="text-xs text-red-400 flex-shrink-0">▼ 리스크</span>
                <span className="text-xs text-gray-400">{item.risk}</span>
              </div>
              <div className="flex gap-1.5">
                <span className="text-xs text-green-400 flex-shrink-0">▲ 기회</span>
                <span className="text-xs text-gray-400">{item.opportunity}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {data.structural_analysis && (
        <div className="bg-gray-900 border border-blue-500/20 rounded-xl p-5">
          <h3 className="text-xs font-bold text-blue-400 mb-3">구조적 대전환 & 생존 전략</h3>
          <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line">
            {data.structural_analysis}
          </p>
        </div>
      )}
    </div>
  );
}

// ── 메인 컴포넌트 ──────────────────────────────────
const RUN_LABEL: Record<string, string> = {
  morning: '06시 브리핑',
  afternoon: '18시 브리핑',
};

export default function ReportsClient() {
  const [report, setReport] = useState<Report | null>(null);
  const [sessions, setSessions] = useState<ReportSession[]>([]);
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedRunType, setSelectedRunType] = useState<'morning' | 'afternoon'>('morning');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const availableRunTypes = (date: string) =>
    sessions.filter(s => s.date === date).map(s => s.run_type);

  const loadInitial = () => {
    setLoading(true);
    setError(null);
    Promise.all([api.reportsList(), api.latestReport()])
      .then(([list, r]) => {
        setSessions(list.sessions ?? []);
        setDates(list.dates);
        setReport(r);
        setSelectedDate(r.date);
        setSelectedRunType(r.run_type ?? 'morning');
      })
      .catch((e: unknown) => setError(`오류: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadInitial(); }, []);

  const handleDateChange = async (date: string) => {
    const types = sessions.filter(s => s.date === date).map(s => s.run_type);
    const rt = types.includes('morning') ? 'morning' : (types[0] ?? 'morning');
    setSelectedDate(date);
    setSelectedRunType(rt);
    await loadReport(date, rt);
  };

  const handleRunTypeChange = async (rt: 'morning' | 'afternoon') => {
    setSelectedRunType(rt);
    await loadReport(selectedDate, rt);
  };

  const loadReport = async (date: string, rt: 'morning' | 'afternoon') => {
    setLoading(true);
    try {
      const r = await api.reportByDate(date, rt);
      setReport(r);
      setError(null);
    } catch {
      setError("해당 브리핑을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <div className="text-gray-400 text-sm">브리핑 불러오는 중...</div>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-red-400 text-sm">{error}</div>
        <button
          onClick={loadInitial}
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-300 hover:bg-gray-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-8">
      {/* 헤더 */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Link href="/" className="text-gray-500 text-xs hover:text-gray-300">← 대시보드</Link>
          </div>
          <h1 className="text-xl font-bold mt-1">
            <span className="text-blue-400">글로벌</span> 브리핑
          </h1>
          <p className="text-gray-500 text-xs mt-0.5">정치·경제·안보·시장 통합 분석</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {dates.length > 0 && (
            <select
              value={selectedDate}
              onChange={e => handleDateChange(e.target.value)}
              aria-label="브리핑 날짜 선택"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 min-h-[44px] text-xs text-gray-300"
            >
              {dates.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          )}
          {selectedDate && availableRunTypes(selectedDate).length > 0 && (
            <div className="flex rounded-lg overflow-hidden border border-gray-700" role="group" aria-label="브리핑 시간 선택">
              {(['morning', 'afternoon'] as const).filter(rt => availableRunTypes(selectedDate).includes(rt)).map(rt => (
                <button
                  key={rt}
                  onClick={() => handleRunTypeChange(rt)}
                  className={`px-3 py-2 min-h-[44px] text-xs font-medium transition-colors ${
                    selectedRunType === rt
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {RUN_LABEL[rt]}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <div className="text-red-400 text-sm bg-red-900/20 border border-red-700/30 rounded-xl px-4 py-3">{error}</div>}

      {report && (
        <>
          <div className="text-xs text-gray-400">
            생성: {new Date(report.generated_at).toLocaleString("ko-KR")} · 기사 {report.articles_count}건 분석
          </div>

          <div className={loading ? "opacity-40 pointer-events-none transition-opacity" : "transition-opacity"}>
            <div className="space-y-10">
              <section>
                <SectionHeader num="①" title="언론사별 헤드라인" />
                <Section1 headlines={report.sections.headlines} />
              </section>

              <section>
                <SectionHeader num="②" title="주요 이슈 TOP 5 입체 분석" />
                <Section2 issues={report.sections.top_issues} />
              </section>

              <section>
                <SectionHeader num="③" title="핵심 이슈별 주요국 입장 대조" />
                <Section3 stances={report.sections.country_stances} />
              </section>

              <section>
                <SectionHeader num="④" title="데이터 통합 리서치 및 연계 분석" />
                <Section4 data={report.sections.market_data} />
              </section>

              <section>
                <SectionHeader num="⑤" title="48시간 내 리스크 Watchlist" />
                <Section5 watchlist={report.sections.risk_watchlist} />
              </section>

              <section>
                <SectionHeader num="⑥" title="글로벌 이슈 총괄 Summary Matrix" />
                <Section6 data={report.sections.summary_matrix} />
              </section>
            </div>
          </div>
        </>
      )}

      {!report && !loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <BookOpen size={32} className="text-gray-600" />
          <p className="text-gray-300 font-medium">생성된 브리핑이 없습니다</p>
          <p className="text-xs text-gray-500">파이프라인 실행 후 자동으로 생성됩니다.</p>
        </div>
      )}
    </div>
  );
}
