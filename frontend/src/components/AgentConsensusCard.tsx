"use client";

import { useState } from "react";
import { AgentDebate } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus, Scale, ChevronDown, ChevronUp } from "lucide-react";

type Props = {
  debate: AgentDebate;
};

const DIRECTION_ICON = (dir: string) => {
  if (dir === "상승") return <TrendingUp size={14} className="text-green-400" />;
  if (dir === "하락") return <TrendingDown size={14} className="text-red-400" />;
  return <Minus size={14} className="text-gray-400" />;
};

const DIRECTION_COLOR = (dir: string) =>
  dir === "상승" ? "text-green-400" : dir === "하락" ? "text-red-400" : "text-gray-400";

export default function AgentConsensusCard({ debate }: Props) {
  const { bull, bear, consensus } = debate;
  const bullW = consensus.bull_weight ?? 50;
  const bearW = consensus.bear_weight ?? 50;
  const [bullOpen, setBullOpen] = useState(false);
  const [bearOpen, setBearOpen] = useState(false);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-4">
      {/* 헤더 */}
      <div className="flex items-center gap-2">
        <Scale size={16} className="text-purple-400" />
        <h3 className="text-sm font-semibold text-gray-300">AI 에이전트 토론</h3>
        <span className="ml-auto text-xs text-gray-500">Bull vs Bear</span>
      </div>

      {/* Bull / Bear 두 컬럼 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Bull */}
        <div className="bg-green-900/10 border border-green-500/20 rounded-lg overflow-hidden">
          <button
            className="w-full flex items-center gap-1.5 p-3 hover:bg-green-900/20 transition-colors"
            onClick={() => setBullOpen(!bullOpen)}
            aria-expanded={bullOpen}
          >
            <TrendingUp size={13} className="text-green-400" />
            <span className="text-xs font-semibold text-green-400">강세론 (Bull)</span>
            <span className="ml-auto text-xs text-green-400/70">{bull.confidence}%</span>
            {bullOpen
              ? <ChevronUp size={12} className="text-green-400/50 ml-1" />
              : <ChevronDown size={12} className="text-green-400/50 ml-1" />}
          </button>
          {bullOpen && (
            <div className="px-3 pb-3 space-y-1.5">
              {bull.bull_case && (
                <p className="text-xs text-gray-300 leading-relaxed">{bull.bull_case}</p>
              )}
              {bull.key_catalyst && (
                <div className="text-xs text-green-400/80">
                  핵심 모멘텀: <span className="text-green-300">{bull.key_catalyst}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Bear */}
        <div className="bg-red-900/10 border border-red-500/20 rounded-lg overflow-hidden">
          <button
            className="w-full flex items-center gap-1.5 p-3 hover:bg-red-900/20 transition-colors"
            onClick={() => setBearOpen(!bearOpen)}
            aria-expanded={bearOpen}
          >
            <TrendingDown size={13} className="text-red-400" />
            <span className="text-xs font-semibold text-red-400">약세론 (Bear)</span>
            <span className="ml-auto text-xs text-red-400/70">{bear.confidence}%</span>
            {bearOpen
              ? <ChevronUp size={12} className="text-red-400/50 ml-1" />
              : <ChevronDown size={12} className="text-red-400/50 ml-1" />}
          </button>
          {bearOpen && (
            <div className="px-3 pb-3 space-y-1.5">
              {bear.bear_case && (
                <p className="text-xs text-gray-300 leading-relaxed">{bear.bear_case}</p>
              )}
              {bear.key_risk && (
                <div className="text-xs text-red-400/80">
                  핵심 리스크: <span className="text-red-300">{bear.key_risk}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 비중 바 */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-500">
          <span>강세 {bullW}%</span>
          <span>약세 {bearW}%</span>
        </div>
        <div className="flex h-2 rounded-full overflow-hidden bg-gray-800">
          <div
            className="bg-green-500/60 transition-all"
            style={{ width: `${bullW}%` }}
          />
          <div
            className="bg-red-500/60 transition-all"
            style={{ width: `${bearW}%` }}
          />
        </div>
      </div>

      {/* 중재자 결론 */}
      {consensus.consensus && (
        <div className="bg-purple-900/10 border border-purple-500/20 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Scale size={12} className="text-purple-400" />
            <span className="text-xs font-semibold text-purple-400">중재자 결론</span>
            <div className={`ml-auto flex items-center gap-1 text-xs font-bold ${DIRECTION_COLOR(consensus.net_direction)}`}>
              {DIRECTION_ICON(consensus.net_direction)}
              {consensus.net_direction}
            </div>
          </div>
          <p className="text-xs text-gray-300 leading-relaxed">{consensus.consensus}</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
            {consensus.key_opportunity && (
              <div className="text-xs">
                <span className="text-green-400/70">기회: </span>
                <span className="text-gray-400">{consensus.key_opportunity}</span>
              </div>
            )}
            {consensus.key_risk && (
              <div className="text-xs">
                <span className="text-red-400/70">리스크: </span>
                <span className="text-gray-400">{consensus.key_risk}</span>
              </div>
            )}
          </div>
          {consensus.agent_confidence != null && (
            <div className="text-xs text-gray-500 text-right">
              신뢰도 {consensus.agent_confidence}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}
