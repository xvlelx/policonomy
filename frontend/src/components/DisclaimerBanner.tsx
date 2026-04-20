"use client";

import { useState, useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";

const STORAGE_KEY = "policonomy_disclaimer_dismissed";

export default function DisclaimerBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (!dismissed) setVisible(true);
  }, []);

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div className="flex items-start gap-3 bg-yellow-900/20 border border-yellow-600/30 rounded-xl px-4 py-3">
      <AlertTriangle size={14} className="text-yellow-400 mt-0.5 flex-shrink-0" />
      <p className="text-xs text-yellow-300/80 leading-relaxed flex-1">
        이 탭의 지표는 <strong>공식 금융 데이터가 아닌 비공식 참고 지표</strong>입니다.
        투자 권유나 투자 조언이 아니며, 의사결정에 단독으로 활용하지 마세요.
      </p>
      <button onClick={dismiss} className="text-yellow-600 hover:text-yellow-400 flex-shrink-0">
        <X size={13} />
      </button>
    </div>
  );
}
