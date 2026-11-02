"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NewsletterPage() {
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/newsletter`)
      .then((r) => {
        if (!r.ok) throw new Error("뉴스레터 없음");
        return r.text();
      })
      .then(setHtml)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="flex items-center gap-3 mb-6">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-gray-400 hover:text-gray-200 text-sm transition-colors"
          >
            <ArrowLeft size={16} />
            대시보드로
          </Link>
          <span className="text-gray-600">/</span>
          <span className="text-gray-300 text-sm font-medium">주간 뉴스레터</span>
        </div>

        {loading && (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <div className="text-gray-400 text-sm">뉴스레터 불러오는 중...</div>
          </div>
        )}
        {error && (
          <div className="text-center py-20 text-red-400">{error}</div>
        )}
        {html && (
          <div className="bg-white rounded-xl overflow-hidden shadow-2xl">
            <iframe
              srcDoc={html}
              className="w-full border-0 min-h-[400px] h-[70dvh] sm:h-[80dvh]"
              title="주간 뉴스레터"
              sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            />
          </div>
        )}
      </div>
    </div>
  );
}
