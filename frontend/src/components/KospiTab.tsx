"use client";

import { Predictions } from "@/lib/api";
import ArticleFilterTab from "./ArticleFilterTab";

const CATEGORIES = ["politics_economy", "real_estate"];
const CATEGORY_LABELS: Record<string, string> = {
  politics_economy: "정치·경제",
  real_estate: "부동산",
};

type Props = { predictions: Predictions };

export default function KospiTab({ predictions }: Props) {
  const debate =
    predictions.fused_analysis?.kospi_debate ??
    predictions.fused_analysis?.agent_debate ??
    undefined;

  return (
    <ArticleFilterTab
      predictions={predictions}
      defaultCategory="politics_economy"
      categories={CATEGORIES}
      categoryLabels={CATEGORY_LABELS}
      marketKeys={["kospi", "usd_krw", "samsung", "skhynix"]}
      debate={debate}
    />
  );
}
