"use client";

import DisclaimerBanner from "./DisclaimerBanner";
import FearGreedCard from "./FearGreedCard";
import HedgeFund13F from "./HedgeFund13F";

export default function UnofficialIndicatorsTab() {
  return (
    <div className="space-y-4">
      <DisclaimerBanner />

      {/* Fear & Greed Index */}
      <FearGreedCard />

      {/* 헤지펀드 13F 포지션 */}
      <HedgeFund13F />
    </div>
  );
}
