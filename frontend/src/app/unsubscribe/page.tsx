"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";

type Status = "idle" | "loading" | "success" | "invalid" | "error";

function UnsubscribeContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") ?? "";
  const token = searchParams.get("token") ?? "";
  const hasParams = email !== "" && token !== "";
  const [status, setStatus] = useState<Status>("idle");

  // 메일 클라이언트의 링크 프리페치로 자동 해지되지 않도록 버튼 클릭 시에만 요청
  const handleConfirm = async () => {
    setStatus("loading");
    try {
      await api.unsubscribe(email, token);
      setStatus("success");
    } catch (e) {
      setStatus(e instanceof ApiError && e.status === 403 ? "invalid" : "error");
    }
  };

  if (!hasParams || status === "invalid") {
    return (
      <Result
        title="수신거부 실패"
        tone="error"
        message="링크가 유효하지 않습니다. 메일에 있는 최신 수신거부 링크를 사용해 주세요."
      />
    );
  }

  if (status === "success") {
    return (
      <Result
        title="수신거부 완료"
        tone="success"
        message="뉴스레터 수신이 해지되었습니다. 이용해 주셔서 감사합니다."
      />
    );
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center space-y-4">
      <h1 className="text-lg font-bold text-gray-100">수신거부 확인</h1>
      <p className="text-sm text-gray-400 leading-relaxed">
        <span className="text-gray-200 break-all">{email}</span> 주소의 뉴스레터 수신을 해지합니다.
      </p>
      {status === "error" && (
        <p role="status" className="text-sm text-red-400">
          처리 중 오류가 발생했습니다. 다시 시도해 주세요.
        </p>
      )}
      <button
        type="button"
        onClick={handleConfirm}
        disabled={status === "loading"}
        className="w-full min-h-[44px] px-4 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
      >
        {status === "loading" ? "처리 중..." : "수신거부 확인"}
      </button>
      <Link href="/" className="inline-flex items-center justify-center min-h-[44px] text-xs text-gray-500 hover:text-gray-300">
        홈으로
      </Link>
    </div>
  );
}

function Result({ title, tone, message }: { title: string; tone: "success" | "error"; message: string }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center space-y-4">
      <h1 className="text-lg font-bold text-gray-100">{title}</h1>
      <p role="status" className={`text-sm leading-relaxed ${tone === "success" ? "text-green-400" : "text-red-400"}`}>
        {message}
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

export default function UnsubscribePage() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <Suspense
          fallback={
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 text-center text-sm text-gray-400">
              불러오는 중...
            </div>
          }
        >
          <UnsubscribeContent />
        </Suspense>
      </div>
    </div>
  );
}
