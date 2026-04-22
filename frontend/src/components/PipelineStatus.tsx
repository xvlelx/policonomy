"use client";

import { useState } from "react";
import { PipelineStatus as PS, api } from "@/lib/api";

type Props = { status: PS; onPipelineStart?: () => void };

export default function PipelineStatus({ status, onPipelineStart }: Props) {
  const isRunning = status.status === "running";
  const isCompleted = status.status === "completed";

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [adminKey, setAdminKey] = useState("");

  const statusColor = isRunning
    ? "text-yellow-400 bg-yellow-400/10 border-yellow-400/30"
    : isCompleted
    ? "text-green-400 bg-green-400/10 border-green-400/30"
    : "text-gray-400 bg-gray-800 border-gray-700";

  const dotColor = isRunning
    ? "bg-yellow-400"
    : isCompleted
    ? "bg-green-400"
    : "bg-gray-500";

  async function handleRun() {
    if (running) return;
    setRunning(true);
    if (!adminKey) {
      setShowKeyInput(true);
      setRunning(false);
      return;
    }
    setError(null);
    try {
      await api.runPipeline(adminKey);
      setShowKeyInput(false);
      onPipelineStart?.();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("409")) {
        setError("이미 실행 중입니다");
      } else if (msg.includes("403")) {
        setError("관리자 키가 틀렸습니다");
        setShowKeyInput(true);
      } else {
        setError(msg);
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        className={`flex flex-wrap items-center gap-3 px-4 py-2.5 rounded-xl border text-sm ${statusColor}`}
      >
        <div className="flex items-center gap-2 flex-shrink-0">
          <div
            className={`w-2 h-2 rounded-full ${dotColor} ${isRunning ? "animate-pulse" : ""}`}
          />
          <span className="font-medium">
            {isRunning
              ? "파이프라인 실행 중"
              : isCompleted
              ? "파이프라인 완료"
              : "대기 중"}
          </span>
        </div>
        {status.stage && (
          <span className="text-xs opacity-75">{status.stage}</span>
        )}
        {status.progress_pct !== null && (
          <div className="flex items-center gap-2 ml-auto">
            <div className="w-20 sm:w-32 bg-black/20 rounded-full h-1.5">
              <div
                className="bg-yellow-400 h-1.5 rounded-full transition-all"
                style={{ width: `${status.progress_pct}%` }}
              />
            </div>
            <span className="text-xs">{status.progress_pct}%</span>
          </div>
        )}
        {status.last_updated && (
          <span className="text-xs opacity-50 ml-auto">
            {status.last_updated}
          </span>
        )}

        {/* 지금 실행 버튼 */}
        {!isRunning && !isCompleted && (
          <button
            onClick={handleRun}
            disabled={running}
            className="ml-auto flex-shrink-0 px-3 py-1 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {running ? "시작 중..." : "지금 실행"}
          </button>
        )}
      </div>

      {/* 관리자 키 입력 */}
      {showKeyInput && (
        <div className="flex gap-2 items-center">
          <input
            type="password"
            placeholder="관리자 키 입력"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleRun()}
            className="flex-1 px-3 py-1.5 text-sm rounded-lg bg-gray-800 border border-gray-600 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleRun}
            disabled={running || !adminKey}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50 transition-colors"
          >
            확인
          </button>
          <button
            onClick={() => setShowKeyInput(false)}
            className="px-3 py-1.5 text-xs rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
          >
            취소
          </button>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 px-1">{error}</p>
      )}
    </div>
  );
}
