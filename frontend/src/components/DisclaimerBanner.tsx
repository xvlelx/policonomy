"use client";

import { useSyncExternalStore } from "react";
import { AlertTriangle, X } from "lucide-react";

const STORAGE_KEY = "policonomy_disclaimer_dismissed";

const listeners = new Set<() => void>();

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

// 저장소 접근이 막힌 환경(사생활 보호 모드 등)에서는 배너를 보여준다
function getSnapshot() {
  try {
    return localStorage.getItem(STORAGE_KEY) === null;
  } catch {
    return true;
  }
}

function getServerSnapshot() {
  return false;
}

export default function DisclaimerBanner() {
  const visible = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const dismiss = () => {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // 저장 실패 시 이번 세션에서만 숨김
    }
    listeners.forEach((l) => l());
  };

  if (!visible) return null;

  return (
    <div className="flex items-start gap-3 bg-yellow-900/20 border border-yellow-600/30 rounded-xl px-4 py-3">
      <AlertTriangle size={14} className="text-yellow-400 mt-0.5 flex-shrink-0" />
      <p className="text-xs text-yellow-300/80 leading-relaxed flex-1">
        이 탭의 지표는 <strong>공식 금융 데이터가 아닌 비공식 참고 지표</strong>입니다.
        투자 권유나 투자 조언이 아니며, 의사결정에 단독으로 활용하지 마세요.
      </p>
      <button
        onClick={dismiss}
        aria-label="닫기"
        className="-my-3 -mr-3 min-w-[44px] min-h-[44px] flex items-center justify-center text-yellow-600 hover:text-yellow-400 flex-shrink-0"
      >
        <X size={13} />
      </button>
    </div>
  );
}
