"use client";

import { useEffect, useState } from "react";
import { Predictions, ArticlesResponse, api } from "@/lib/api";
import { Search, X } from "lucide-react";
import MarketCards from "./MarketCards";
import AgentConsensusCard from "./AgentConsensusCard";
import ArticleList from "./ArticleList";

const KOSPI_CATEGORIES = ["politics_economy", "real_estate"];
const CATEGORY_LABELS: Record<string, string> = {
  politics_economy: "정치·경제",
  real_estate: "부동산",
};
const SENTIMENT_LABELS = [
  { key: "", label: "전체", active: "bg-gray-600 text-white" },
  { key: "positive", label: "긍정", active: "bg-green-700 text-white" },
  { key: "negative", label: "부정", active: "bg-red-700 text-white" },
  { key: "neutral", label: "중립", active: "bg-gray-600 text-white" },
  { key: "cautious", label: "신중", active: "bg-yellow-700 text-white" },
];

type Props = {
  predictions: Predictions;
};

export default function KospiTab({ predictions }: Props) {
  const [articles, setArticles] = useState<ArticlesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState("politics_economy");
  const [selectedSentiment, setSelectedSentiment] = useState("");
  const [minImportance, setMinImportance] = useState(4);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    setLoading(true);
    setFetchError(false);
    api.articles({
      category: selectedCategory || undefined,
      sentiment: selectedSentiment || undefined,
      min_importance: minImportance,
      page,
      page_size: 10,
    })
      .then(setArticles)
      .catch(() => setFetchError(true))
      .finally(() => setLoading(false));
  }, [selectedCategory, selectedSentiment, minImportance, page]);

  const handleCategory = (cat: string) => { setSelectedCategory(cat); setPage(1); };
  const handleSentiment = (s: string) => { setSelectedSentiment(s); setPage(1); };
  const isFiltered = selectedCategory !== "politics_economy" || selectedSentiment !== "" || minImportance !== 4 || searchQuery !== "";
  const resetFilters = () => { setSelectedCategory("politics_economy"); setSelectedSentiment(""); setMinImportance(4); setPage(1); setSearchQuery(""); };

  return (
    <div className="space-y-4">
      {/* 국장 시장 예측 카드 */}
      <MarketCards predictions={predictions} markets={["kospi", "usd_krw", "samsung", "skhynix"]} />

      {/* AI 에이전트 토론 */}
      {(predictions.fused_analysis?.kospi_debate ?? predictions.fused_analysis?.agent_debate) && (
        <AgentConsensusCard debate={(predictions.fused_analysis.kospi_debate ?? predictions.fused_analysis.agent_debate)!} />
      )}

      {/* 국장 관련 뉴스 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-400">관련 기사</h3>
          {isFiltered && (
            <button onClick={resetFilters} className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors">
              <X size={12} /> 필터 초기화
            </button>
          )}
        </div>

        {/* 카테고리 필터 */}
        <div className="flex flex-wrap gap-2">
          {["", ...KOSPI_CATEGORIES].map((cat) => (
            <button
              key={cat}
              onClick={() => handleCategory(cat)}
              className={`px-3 py-2 min-h-[44px] rounded-lg text-xs font-medium transition-colors ${
                selectedCategory === cat
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {cat ? CATEGORY_LABELS[cat] : "전체"}
            </button>
          ))}
        </div>

        {/* 감성 + 중요도 필터 */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-2 flex-1">
            {SENTIMENT_LABELS.map(({ key, label, active }) => (
              <button
                key={key}
                onClick={() => handleSentiment(key)}
                className={`px-3 py-2 min-h-[44px] rounded-lg text-xs font-medium transition-colors ${
                  selectedSentiment === key
                    ? active
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400 flex-shrink-0">
            <span className="hidden sm:inline">중요도 ≥</span>
            <select
              value={minImportance}
              onChange={(e) => { setMinImportance(Number(e.target.value)); setPage(1); }}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 text-xs min-h-[44px]"
            >
              {[3, 4, 5, 6, 7, 8].map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 키워드 검색 */}
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="제목으로 검색..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-8 pr-3 py-2 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-600 transition-colors"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* 기사 목록 */}
      <div className={loading ? "opacity-50 pointer-events-none transition-opacity" : "transition-opacity"}>
        {articles && articles.items.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-500 text-sm">조건에 맞는 기사가 없습니다.</div>
        )}
        {articles && articles.items.length > 0 && (
          <ArticleList articles={articles} page={page} onPageChange={setPage} searchQuery={searchQuery} />
        )}
      </div>
      {fetchError && (
        <div className="text-center py-8 text-red-400 text-sm">기사를 불러오지 못했습니다.</div>
      )}
      {loading && !articles && (
        <div className="space-y-2.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-gray-900 rounded-xl border border-gray-700/60 p-4 animate-pulse">
              <div className="h-3 bg-gray-800 rounded w-1/4 mb-2" />
              <div className="h-4 bg-gray-800 rounded w-3/4 mb-1" />
              <div className="h-3 bg-gray-800 rounded w-1/2" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
