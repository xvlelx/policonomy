"use client";

type Tab = "kospi" | "us" | "unofficial";

type Props = {
  active: Tab;
  onChange: (tab: Tab) => void;
};

const TABS: { key: Tab; label: string; sub: string }[] = [
  { key: "kospi", label: "국내", sub: "KOSPI · 원달러 · 삼성" },
  { key: "us", label: "해외", sub: "NASDAQ · S&P500 · NVIDIA" },
  { key: "unofficial", label: "심리지표", sub: "Fear & Greed · 헤지펀드" },
];

export default function DashboardTabs({ active, onChange }: Props) {
  return (
    <div className="border-b border-gray-800">
      <div role="tablist" className="flex gap-0">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            id={`tab-${t.key}`}
            aria-selected={active === t.key}
            aria-controls={`panel-${t.key}`}
            onClick={() => onChange(t.key)}
            onKeyDown={(e) => {
              const idx = TABS.findIndex((x) => x.key === active);
              if (e.key === "ArrowRight" && idx < TABS.length - 1) onChange(TABS[idx + 1].key);
              if (e.key === "ArrowLeft" && idx > 0) onChange(TABS[idx - 1].key);
            }}
            className={`relative px-4 sm:px-6 py-3 min-h-[44px] text-sm font-semibold transition-colors text-left flex flex-col sm:flex-row sm:items-center sm:gap-2 justify-center ${
              active === t.key
                ? "text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            <span>{t.label}</span>
            <span className={`hidden sm:inline text-xs font-normal ${active === t.key ? "text-gray-400" : "text-gray-600"}`}>
              {t.sub}
            </span>
            {active === t.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-t-full" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
