"use client";

import { Predictions } from "@/lib/api";
import ArticleFilterTab from "./ArticleFilterTab";
import SectorTrends from "./SectorTrends";

const CATEGORIES = ["global_macro", "tech_industry"];
const CATEGORY_LABELS: Record<string, string> = {
  global_macro: "글로벌",
  tech_industry: "테크",
};

type Props = { predictions: Predictions };

export default function UsMarketTab({ predictions }: Props) {
  const debate =
    predictions.fused_analysis?.us_debate ??
    predictions.fused_analysis?.agent_debate ??
    undefined;

  return (
    <ArticleFilterTab
      predictions={predictions}
      defaultCategory="global_macro"
      categories={CATEGORIES}
      categoryLabels={CATEGORY_LABELS}
      marketKeys={["nasdaq", "sp500", "dow", "nvidia"]}
      debate={debate}
      extraSection={<SectorTrends />}
    />
  );
}
