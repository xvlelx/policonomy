"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Status = "loading" | "success" | "invalid" | "error";

const MESSAGES: Record<Status, string> = {
  loading: "구독 확인 중...",
  success: "구독이 확인되었습니다. 매일 밤 AI 분석 요약을 보내드릴게요.",
  invalid: "링크가 만료되었거나 유효하지 않습니다. 다시 구독 신청해 주세요.",
  error: "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
};

function ConfirmContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<Status>(token ? "loading" : "invalid");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    api
      .confirm(token)
      .then(() => { if (!cancelled) setStatus("success"); })
      .catch((e: unknown) => {
        if (cancelled) return;
        setStatus(e instanceof ApiError && e.status === 400 ? "invalid" : "error");
      });
    return () => { cancelled = true; };
  }, [token]);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center space-y-4">
      {status === "loading" && (
        <div className="mx-auto w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      )}
      <h1 className="text-lg font-bold text-gray-100">
        {status === "success" ? "구독 확인 완료" : status === "loading" ? "잠시만 기다려 주세요" : "구독 확인"}
      </h1>
      <p
        role="status"
        className={`text-sm leading-relaxed ${
          status === "success" ? "text-green-400" : status === "loading" ? "text-gray-400" : "text-red-400"
        }`}
      >
        {MESSAGES[status]}
      </p>
      <Link
        href="/"
        className="inline-flex items-center justify-center min-h-[44px] px-4 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors"
      >
        홈으로
      </Link>
    </div>
  );
}

export default function ConfirmPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Suspense
          fallback={
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-sm text-gray-400">
              구독 확인 중...
            </div>
          }
        >
          <ConfirmContent />
        </Suspense>
      </div>
    </div>
  );
}
