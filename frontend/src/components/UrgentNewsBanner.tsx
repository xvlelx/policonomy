"use client";

import { useEffect, useState } from "react";
import { api, Article } from "@/lib/api";

const CATEGORY_LABELS: Record<string, string> = {
  politics_economy: "정치·경제",
  global_macro: "글로벌",
  tech_industry: "테크",
  real_estate: "부동산",
};

export default function UrgentNewsBanner() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [dismissed, setDismissed] = useState(false);
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    api.articles({ is_urgent: true, min_importance: 1 })
      .then((res) => setArticles(res.items))
      .catch(() => {});
  }, []);

  if (dismissed || articles.length === 0) return null;

  return (
    <div className="rounded-xl border border-red-800 bg-red-950/40 overflow-hidden">
      {/* 배너 헤더 */}
      <button
        type="button"
        aria-expanded={!collapsed}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-red-900/30 border-b border-red-800 hover:bg-red-900/50 transition-colors text-left"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          <span className="text-xs font-semibold text-red-300 uppercase tracking-wide">
            긴급 주목 이슈 {articles.length}건
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-red-500 text-xs">
            {collapsed ? "▼" : "▲"}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); setDismissed(true); }}
            className="text-red-600 hover:text-red-400 text-lg leading-none"
            aria-label="닫기"
          >
            ×
          </button>
        </div>
      </button>

      {/* 기사 목록 */}
      {!collapsed && (
        <div className="divide-y divide-red-900/50">
          {articles.map((article, i) => (
            <a
              key={i}
              href={article.link || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="block px-4 py-3 hover:bg-red-900/20 transition-colors"
            >
              <div className="flex items-start gap-2">
                <span className="text-xs text-red-500 flex-shrink-0 mt-0.5">
                  {CATEGORY_LABELS[article.category] || article.category}
                </span>
                <p className="text-sm text-red-100 leading-snug font-medium">
                  {article.title}
                </p>
              </div>
              {article.one_line && (
                <p className="text-xs text-red-300/70 mt-1 leading-relaxed">
                  {article.one_line}
                </p>
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
