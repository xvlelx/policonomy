"use client";

import { useEffect, useState, useMemo } from "react";
import { api, TopArticle } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  politics_economy: "정치·경제",
  global_macro: "글로벌",
  tech_industry: "테크",
  real_estate: "부동산",
};

const SENTIMENT_STYLES: Record<string, string> = {
  positive: "bg-green-900/50 text-green-300 border-green-800",
  negative: "bg-red-900/50 text-red-300 border-red-800",
  neutral: "bg-gray-800 text-gray-400 border-gray-700",
  cautious: "bg-yellow-900/50 text-yellow-300 border-yellow-800",
};

const SENTIMENT_LABELS: Record<string, string> = {
  positive: "긍정",
  negative: "부정",
  neutral: "중립",
  cautious: "신중",
};

function weekOfMonth(dateStr: string): number {
  const date = new Date(dateStr + "T00:00:00");
  return Math.ceil(date.getDate() / 7);
}

function weekLabel(weekStr: string): string {
  const date = new Date(weekStr + "T00:00:00");
  const month = date.getMonth() + 1;
  const wom = weekOfMonth(weekStr);
  return `${date.getFullYear()}년 ${month}월 ${wom}째 주`;
}

function ImportanceDots({ value }: { value: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${
            i < value
              ? value >= 8
                ? "bg-red-400"
                : value >= 6
                ? "bg-yellow-400"
                : "bg-blue-400"
              : "bg-gray-700"
          }`}
        />
      ))}
    </div>
  );
}

export default function WeeklyTopArticles() {
  const [weeks, setWeeks] = useState<string[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<string>("");
  const [articles, setArticles] = useState<TopArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  // 필터 상태
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [selectedMonth, setSelectedMonth] = useState<string>("");
  const [selectedWom, setSelectedWom] = useState<string>(""); // week of month

  useEffect(() => {
    api.weeklyTopWeeks().then((res) => {
      setWeeks(res.weeks);
      if (res.weeks.length > 0) {
        const latest = res.weeks[0];
        setSelectedWeek(latest);
        const d = new Date(latest + "T00:00:00");
        setSelectedYear(String(d.getFullYear()));
        setSelectedMonth(String(d.getMonth() + 1));
        setSelectedWom(String(weekOfMonth(latest)));
      }
    });
  }, []);

  // 년도 목록
  const years = useMemo(() => {
    const ys = [...new Set(weeks.map((w) => String(new Date(w + "T00:00:00").getFullYear())))];
    return ys.sort((a, b) => Number(b) - Number(a));
  }, [weeks]);

  // 선택된 년도 기준 월 목록
  const months = useMemo(() => {
    const ms = [
      ...new Set(
        weeks
          .filter((w) => String(new Date(w + "T00:00:00").getFullYear()) === selectedYear)
          .map((w) => String(new Date(w + "T00:00:00").getMonth() + 1))
      ),
    ];
    return ms.sort((a, b) => Number(b) - Number(a));
  }, [weeks, selectedYear]);

  // 선택된 년/월 기준 주차 목록
  const woms = useMemo(() => {
    const ws = [
      ...new Set(
        weeks
          .filter((w) => {
            const d = new Date(w + "T00:00:00");
            return (
              String(d.getFullYear()) === selectedYear &&
              String(d.getMonth() + 1) === selectedMonth
            );
          })
          .map((w) => String(weekOfMonth(w)))
      ),
    ];
    return ws.sort((a, b) => Number(b) - Number(a));
  }, [weeks, selectedYear, selectedMonth]);

  // 년/월/주차 → 실제 week 날짜 매핑
  useEffect(() => {
    if (!selectedYear || !selectedMonth || !selectedWom) return;
    const matched = weeks.find((w) => {
      const d = new Date(w + "T00:00:00");
      return (
        String(d.getFullYear()) === selectedYear &&
        String(d.getMonth() + 1) === selectedMonth &&
        String(weekOfMonth(w)) === selectedWom
      );
    });
    if (matched) setSelectedWeek(matched);
  }, [selectedYear, selectedMonth, selectedWom, weeks]);

  // 년도 변경 시 첫 번째 월/주 자동 선택
  const handleYearChange = (year: string) => {
    setSelectedYear(year);
    const newMonths = [
      ...new Set(
        weeks
          .filter((w) => String(new Date(w + "T00:00:00").getFullYear()) === year)
          .map((w) => String(new Date(w + "T00:00:00").getMonth() + 1))
      ),
    ].sort((a, b) => Number(b) - Number(a));
    const firstMonth = newMonths[0] || "";
    setSelectedMonth(firstMonth);

    const newWoms = [
      ...new Set(
        weeks
          .filter((w) => {
            const d = new Date(w + "T00:00:00");
            return String(d.getFullYear()) === year && String(d.getMonth() + 1) === firstMonth;
          })
          .map((w) => String(weekOfMonth(w)))
      ),
    ].sort((a, b) => Number(b) - Number(a));
    setSelectedWom(newWoms[0] || "");
  };

  // 월 변경 시 첫 번째 주 자동 선택
  const handleMonthChange = (month: string) => {
    setSelectedMonth(month);
    const newWoms = [
      ...new Set(
        weeks
          .filter((w) => {
            const d = new Date(w + "T00:00:00");
            return String(d.getFullYear()) === selectedYear && String(d.getMonth() + 1) === month;
          })
          .map((w) => String(weekOfMonth(w)))
      ),
    ].sort((a, b) => Number(b) - Number(a));
    setSelectedWom(newWoms[0] || "");
  };

  useEffect(() => {
    if (!selectedWeek) return;
    setLoading(true);
    setExpanded(null);
    api
      .weeklyTop(selectedWeek)
      .then((res) => setArticles(res.articles))
      .finally(() => setLoading(false));
  }, [selectedWeek]);

  if (!weeks.length && !loading) {
    return (
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 text-center text-gray-500 text-sm">
        아직 수집된 주간 데이터가 없습니다.
      </div>
    );
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800">
      {/* 헤더 */}
      <div className="px-4 pt-4 pb-3 border-b border-gray-800">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h3 className="text-sm font-semibold text-gray-200">주간 TOP 10 뉴스</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {selectedWeek ? weekLabel(selectedWeek) : ""} · AI 중요도 기준 선별
            </p>
          </div>
          {/* 년/월/주차 필터 */}
          {weeks.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {/* 년도 */}
              <select
                value={selectedYear}
                onChange={(e) => handleYearChange(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300"
              >
                {years.map((y) => (
                  <option key={y} value={y}>{y}년</option>
                ))}
              </select>
              {/* 월 */}
              <select
                value={selectedMonth}
                onChange={(e) => handleMonthChange(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300"
              >
                {months.map((m) => (
                  <option key={m} value={m}>{m}월</option>
                ))}
              </select>
              {/* 주차 */}
              <select
                value={selectedWom}
                onChange={(e) => setSelectedWom(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-gray-300"
              >
                {woms.map((w) => (
                  <option key={w} value={w}>{w}째 주</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* 기사 목록 */}
      <div className="divide-y divide-gray-800">
        {loading ? (
          <div className="py-10 text-center text-gray-500 text-sm">로딩 중...</div>
        ) : articles.length === 0 ? (
          <div className="py-10 text-center text-gray-500 text-sm">데이터 없음</div>
        ) : (
          articles.map((article) => (
            <div key={article.id} className="px-4 py-3">
              <div
                className="flex items-start gap-3 cursor-pointer"
                onClick={() =>
                  setExpanded(expanded === article.id ? null : article.id)
                }
              >
                {/* 순위 */}
                <div
                  className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    article.rank <= 3
                      ? "bg-yellow-500/20 text-yellow-400"
                      : "bg-gray-800 text-gray-500"
                  }`}
                >
                  {article.rank}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-2 flex-wrap">
                    <span className="text-xs text-gray-500 flex-shrink-0">
                      {CATEGORY_LABELS[article.category] || article.category}
                    </span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded border flex-shrink-0 ${
                        SENTIMENT_STYLES[article.sentiment] ?? SENTIMENT_STYLES.neutral
                      }`}
                    >
                      {SENTIMENT_LABELS[article.sentiment] ?? article.sentiment}
                    </span>
                  </div>
                  <p className="text-sm text-gray-200 mt-1 leading-snug line-clamp-2">
                    {article.title}
                  </p>
                  {article.one_line && (
                    <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                      {article.one_line}
                    </p>
                  )}
                  <div className="mt-1.5">
                    <ImportanceDots value={article.importance} />
                  </div>
                </div>
              </div>

              {/* 펼침 상세 */}
              {expanded === article.id && (
                <div className="mt-3 pl-9 space-y-2">
                  {article.economic_impact && (
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">경제적 영향</p>
                      <p className="text-xs text-gray-300 leading-relaxed">
                        {article.economic_impact}
                      </p>
                    </div>
                  )}
                  {article.affected_sectors?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {article.affected_sectors.map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 bg-blue-900/30 text-blue-300 text-xs rounded border border-blue-800/50"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                  {article.link && (
                    <a
                      href={article.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:text-blue-300 underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      원문 보기 →
                    </a>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
