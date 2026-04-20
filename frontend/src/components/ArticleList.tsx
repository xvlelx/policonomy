"use client";

import { useState } from "react";
import { Article, ArticlesResponse, api } from "@/lib/api";
import { ChevronRight, Bell, Search, FileSearch } from "lucide-react";
import ArticleDetailModal from "./ArticleDetailModal";

type Props = {
  articles: ArticlesResponse;
  page: number;
  onPageChange: (p: number) => void;
  searchQuery?: string;
};

const SENTIMENT_BADGE: Record<string, string> = {
  positive: "bg-green-500/20 text-green-400 border-green-500/30",
  negative: "bg-red-500/20 text-red-400 border-red-500/30",
  neutral: "bg-gray-700 text-gray-400 border-gray-600",
  cautious: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  mixed: "bg-purple-500/20 text-purple-400 border-purple-500/30",
};

const SENTIMENT_LABEL: Record<string, string> = {
  positive: "긍정",
  negative: "부정",
  neutral: "중립",
  cautious: "신중",
  mixed: "혼재",
};

const IMPORTANCE_COLOR = (v: number) =>
  v >= 8 ? "text-red-400" : v >= 6 ? "text-yellow-400" : "text-gray-400";

function ArticleCard({ article, onClick }: { article: Article; onClick: () => void }) {
  const sent = article.sentiment || "neutral";

  return (
    <div
      className="bg-gray-900 rounded-xl border border-gray-700/60 hover:border-gray-600 hover:bg-gray-800/40 transition-colors cursor-pointer"
      onClick={onClick}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            <span className={`text-sm font-bold ${IMPORTANCE_COLOR(article.importance)}`}>
              {article.importance}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span
                className={`text-xs px-1.5 py-0.5 rounded border ${SENTIMENT_BADGE[sent]}`}
              >
                {SENTIMENT_LABEL[sent]}
              </span>
              {article.affected_sectors?.slice(0, 2).map((s) => (
                <span key={s} className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
                  {s}
                </span>
              ))}
              {article.is_urgent && (
                <span className="text-xs bg-red-500/10 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded">
                  긴급
                </span>
              )}
            </div>
            <h3 className="text-sm font-medium text-gray-100 leading-snug line-clamp-2">
              {article.title}
            </h3>
            {article.one_line && (
              <p className="text-xs text-gray-400 mt-1 line-clamp-1">{article.one_line}</p>
            )}
            {article.issue && !article.one_line && (
              <p className="text-xs text-gray-400 mt-1 line-clamp-1">{article.issue}</p>
            )}
          </div>
          <div className="flex-shrink-0">
            <ChevronRight size={16} className="text-gray-600" />
          </div>
        </div>
      </div>
    </div>
  );
}

function NewsletterCta() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setState("loading");
    try {
      await api.subscribe(email);
      setState("done");
    } catch (err) {
      console.error("Newsletter subscription failed:", err);
      setState("error");
    }
  };

  if (state === "done") {
    return (
      <div className="rounded-xl border border-green-800/50 bg-green-900/10 px-4 py-3 text-xs text-green-400 text-center">
        구독 완료! 매일 밤 분석 요약을 보내드릴게요.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-blue-800/50 bg-blue-900/10 px-4 py-3">
      <div className="flex items-center gap-2 mb-2.5">
        <Bell size={13} className="text-blue-400 flex-shrink-0" />
        <p className="text-xs text-gray-300">매일 밤 AI 분석 요약을 이메일로 받아보세요</p>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="이메일 주소 입력"
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-600 min-w-0"
          required
        />
        <button
          type="submit"
          disabled={state === "loading"}
          className="sm:flex-shrink-0 text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg transition-colors font-medium"
        >
          {state === "loading" ? "..." : "구독"}
        </button>
      </form>
      {state === "error" && (
        <p className="text-xs text-red-400 mt-1.5">구독 중 오류가 발생했어요. 다시 시도해주세요.</p>
      )}
    </div>
  );
}

export default function ArticleList({ articles, page, onPageChange, searchQuery = "" }: Props) {
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  const filtered = searchQuery.trim()
    ? articles.items.filter((a) => a.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : articles.items;

  if (!filtered.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-center">
        <FileSearch size={28} className="text-gray-600" aria-hidden="true" />
        <p className="text-sm text-gray-400">
          {searchQuery ? `"${searchQuery}" 검색 결과 없음` : "해당 조건의 기사가 없습니다"}
        </p>
        <p className="text-xs text-gray-600">필터 조건을 변경해보세요</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-400">
            심층 분석 기사{" "}
            <span className="text-gray-500">
              ({searchQuery ? `${filtered.length} / ${articles.total}건` : `${articles.total}건`})
            </span>
          </h2>
        </div>

        <div className="space-y-2.5">
          {filtered.map((article, i) => (
            <ArticleCard
              key={article.link || `${article.title}-${i}`}
              article={article}
              onClick={() => setSelectedArticle(article)}
            />
          ))}
        </div>

        {/* 뉴스레터 구독 CTA */}
        {page === 1 && <NewsletterCta />}

        {/* 페이지네이션 */}
        {articles.pages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t border-gray-800">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-400 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← 이전
            </button>
            <span className="text-xs text-gray-500">
              <span className="text-gray-300 font-medium">{page}</span> / {articles.pages} 페이지
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= articles.pages}
              className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-xs text-gray-400 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              다음 →
            </button>
          </div>
        )}
      </div>

      {selectedArticle && (
        <ArticleDetailModal
          article={selectedArticle}
          onClose={() => setSelectedArticle(null)}
        />
      )}
    </>
  );
}
