"use client";

import { useEffect, useRef } from "react";
import { Article } from "@/lib/api";
import { ExternalLink, X, TrendingUp, TrendingDown, Minus } from "lucide-react";

type Props = {
  article: Article;
  onClose: () => void;
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

const CATEGORY_LABELS: Record<string, string> = {
  politics_economy: "정치·경제",
  global_macro: "글로벌",
  tech_industry: "테크",
  real_estate: "부동산",
};

export default function ArticleDetailModal({ article, onClose }: Props) {
  const sent = article.sentiment || "neutral";
  const isUp = sent === "positive";
  const isDown = sent === "negative";
  const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.body.style.overflow = "hidden";
    const firstFocusable = panelRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, [tabindex]:not([tabindex="-1"])'
    );
    firstFocusable?.focus();
    return () => { document.body.style.overflow = ""; };
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") { onClose(); return; }
    if (e.key !== "Tab") return;
    const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable?.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
      e.preventDefault();
      (e.shiftKey ? last : first).focus();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      onClick={onClose}
    >
      {/* 오버레이 */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

      {/* 모달 패널 */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="relative w-full sm:max-w-2xl max-h-[90dvh] overflow-y-auto bg-gray-900 rounded-t-2xl sm:rounded-2xl border border-gray-700 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* 모바일 드래그 핸들 */}
        <div className="sm:hidden flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 bg-gray-600 rounded-full" />
        </div>

        {/* 헤더 */}
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-5 py-4 flex items-start gap-3 z-10">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className={`text-xs px-1.5 py-0.5 rounded border ${SENTIMENT_BADGE[sent]}`}>
                {SENTIMENT_LABEL[sent]}
              </span>
              <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
                {CATEGORY_LABELS[article.category] || article.category}
              </span>
              <span className={`text-xs font-bold ${IMPORTANCE_COLOR(article.importance)}`}>
                중요도 {article.importance}
              </span>
              {article.is_urgent && (
                <span className="text-xs bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded">
                  긴급
                </span>
              )}
            </div>
            <h2 id="modal-title" className="text-sm font-semibold text-gray-100 leading-snug">{article.title}</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="닫기"
            className="-mr-2 -my-2 flex-shrink-0 w-11 h-11 flex items-center justify-center rounded-lg hover:bg-gray-800 text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* 본문 */}
        <div className="px-5 py-4 space-y-4">
          {/* 한줄 요약 */}
          {article.one_line && (
            <div className="flex items-start gap-2 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
              <Icon size={14} className={isUp ? "text-green-400" : isDown ? "text-red-400" : "text-gray-400"} />
              <p className="text-sm text-gray-200 leading-relaxed">{article.one_line}</p>
            </div>
          )}

          {/* 핵심 이슈 */}
          {article.issue && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">핵심 이슈</h3>
              <p className="text-sm text-gray-300 leading-relaxed">{article.issue}</p>
            </div>
          )}

          {/* 원인·배경 */}
          {article.cause && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">원인·배경</h3>
              <p className="text-sm text-gray-300 leading-relaxed">{article.cause}</p>
            </div>
          )}

          {/* 경제적 영향 */}
          {article.economic_impact && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">경제적 영향</h3>
              <p className="text-sm text-gray-300 leading-relaxed">{article.economic_impact}</p>
            </div>
          )}

          {/* AI 예측 */}
          {article.prediction && (
            <div className="p-3 bg-blue-900/20 rounded-lg border border-blue-500/20">
              <h3 className="text-xs font-semibold text-blue-400 mb-1.5">AI 예측</h3>
              <p className="text-sm text-gray-300 leading-relaxed">{article.prediction}</p>
            </div>
          )}

          {/* 영향 섹터 */}
          {article.affected_sectors && article.affected_sectors.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">영향 섹터</h3>
              <div className="flex flex-wrap gap-1.5">
                {article.affected_sectors.map((s) => (
                  <span key={s} className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded-md border border-gray-700">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 키워드 */}
          {article.keywords && article.keywords.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">키워드</h3>
              <div className="flex flex-wrap gap-1.5">
                {article.keywords.map((k) => (
                  <span key={k} className="text-xs bg-blue-900/30 text-blue-300 px-2 py-0.5 rounded-md">
                    #{k}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 푸터 */}
        {article.link && (
          <div className="sticky bottom-0 bg-gray-900 border-t border-gray-800 px-5 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
            <a
              href={article.link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl transition-colors"
            >
              원문 보기 <ExternalLink size={14} />
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
