const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

export type Article = {
  issue: string
  cause: string
  economic_impact: string
  affected_sectors: string[]
  sentiment: 'positive' | 'negative' | 'neutral' | 'cautious'
  prediction: string
  importance: number
  title: string
  link: string
  category: string
  one_line?: string
  is_urgent?: boolean
  keywords?: string[]
}

export type MarketPred = {
  name: string
  last_close: number
  pred_close: number
  change_pct: number
  direction: string
  pred_range: { high: number; low: number }
}

export type XgbPred = {
  direction: string
  confidence: number
  source: string
}

export type NewsImpactItem = {
  category: string
  label: string
  positive: number
  negative: number
  neutral: number
  total: number
  net_score: number  // -1 ~ +1
  markets: string[]
}

export type AgentDebate = {
  bull: { bull_case: string; key_catalyst: string; target_markets: string[]; confidence: number }
  bear: { bear_case: string; key_risk: string; vulnerable_markets: string[]; confidence: number }
  consensus: {
    consensus: string
    bull_weight: number
    bear_weight: number
    net_direction: string
    key_risk: string
    key_opportunity: string
    agent_confidence: number
  }
}

export type Predictions = {
  generated_at: string
  kronos_predictions: Record<string, MarketPred>
  xgb_predictions?: Record<string, XgbPred>
  fused_analysis: {
    kospi: { direction: string; reason: string; confidence: number }
    usd_krw: { direction: string; reason: string; confidence: number }
    key_sector: { name: string; direction: string; reason: string; confidence: number }
    overall_sentiment: string
    weekly_summary: string
    news_impact?: NewsImpactItem[]
    agent_debate?: AgentDebate
    kospi_debate?: AgentDebate
    us_debate?: AgentDebate
  }
  last_verification?: unknown
  accuracy?: unknown
  model_accuracy?: Record<string, number | null>
}

export type ArticlesResponse = {
  items: Article[]
  total: number
  page: number
  pages: number
}

// ── Reports ──────────────────────────────────────────
export type ReportHeadline = {
  outlet: string
  region: string
  title: string
  link: string
  sentiment: string
  importance: number
  category: string
  one_line: string
}

export type ReportIssue = {
  rank: number
  title: string
  summary: string
  political_intent: string
  economic_interest: string
  framing: string
  security_angle: string
  market_impact: string
  sentiment: string
}

export type CountryStance = {
  country: string
  flag: string
  official_position: string
  real_intent: string
  stance_type: string
}

export type CountryStances = {
  issue_title: string
  countries: CountryStance[]
}

export type MarketDataItem = {
  market: string
  last_close: number | null
  pred_close: number | null
  change_pct: number | null
  pred_range: { high: number; low: number }
  xgb_direction: string | null
  xgb_confidence: number | null
  ai_confidence: number | null
  ai_reason: string | null
}

export type RiskItem = {
  event: string
  scenario: string
  expected_trend: string
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW'
  affected_markets: string[]
}

export type MatrixItem = {
  category: string
  category_en: string
  status: string
  key_trend: string
  risk: string
  opportunity: string
}

export type ReportSession = {
  date: string
  run_type: 'morning' | 'afternoon'
}

export type Report = {
  date: string
  run_type?: 'morning' | 'afternoon'
  generated_at: string
  articles_count: number
  sections: {
    headlines: ReportHeadline[]
    top_issues: ReportIssue[]
    country_stances: CountryStances[]
    market_data: {
      market_items: MarketDataItem[]
      news_impact: NewsImpactItem[]
      key_sector: { name: string; direction: string; reason: string } | null
      overall_sentiment: string | null
    }
    risk_watchlist: RiskItem[]
    summary_matrix: {
      matrix: MatrixItem[]
      structural_analysis: string
    }
  }
}
// ─────────────────────────────────────────────────────

export type ArticleStats = {
  total_articles: number
  by_category: Record<string, number>
  by_sentiment: Record<string, number>
  top_sectors: { name: string; count: number }[]
}

export type PipelineStatus = {
  status: 'idle' | 'running' | 'completed' | 'unknown'
  stage: string | null
  progress: number | null
  total: number | null
  progress_pct: number | null
  last_updated: string | null
}

export type UserSettings = {
  categories: string[]
  email: string
  email_notifications: boolean
}

export type Accuracy = {
  days: number
  direction_accuracy: number
  total_predictions: number
}

export type Summary = {
  pipeline: PipelineStatus
  articles_analyzed: number
  generated_at: string | null
  overall_sentiment: string | null
  weekly_summary: string | null
  accuracy: Accuracy
  kospi: { last_close: number; pred_close: number; change_pct: number; direction: string }
  usd_krw: { last_close: number; pred_close: number; change_pct: number; direction: string }
}

export type TopArticle = {
  id: number
  day?: string
  week?: string
  rank: number
  title: string
  link: string
  category: string
  sentiment: string
  importance: number
  one_line: string
  issue: string
  economic_impact: string
  affected_sectors: string[]
  keywords: string[]
}

export type DailyTopResponse = {
  day: string | null
  articles: TopArticle[]
}

export type WeeklyTopResponse = {
  week: string | null
  articles: TopArticle[]
}

export type WeeklyInsight = {
  week_label: string
  week_start: string
  week_end: string
  days_count: number
  total_articles: number
  avg_politics_sentiment: number | null
  avg_global_sentiment: number | null
  avg_tech_sentiment: number | null
  avg_realestate_sentiment: number | null
  total_hits: number
  total_preds: number
  accuracy: number | null
  avg_kospi_change: number | null
  avg_nasdaq_change: number | null
}

export type MarketCorrelationPoint = {
  day: string
  politics_score: number | null
  global_score: number | null
  tech_score: number | null
  combined_sentiment: number | null
  overall_sentiment: string | null
  kospi_change: number | null
  usdkrw_change: number | null
  samsung_change: number | null
  skhynix_change: number | null
  nasdaq_change: number | null
  sp500_change: number | null
  dow_change: number | null
  nvidia_change: number | null
}

export type SectorTrend = {
  key: string
  label: string
  recent_score: number | null
  prev_score: number | null
  delta: number | null
  direction: 'up' | 'down' | 'flat'
}

export type SectorTrendsResponse = {
  trends: SectorTrend[]
  has_data: boolean
  recent_days?: number
  prev_days?: number
}

export type PredictionRecord = {
  day: string
  kospi_pred_dir: string | null
  kospi_actual_change: number | null
  usdkrw_pred_dir: string | null
  usdkrw_actual_change: number | null
  samsung_pred_dir: string | null
  samsung_actual_change: number | null
  skhynix_pred_dir: string | null
  skhynix_actual_change: number | null
  nasdaq_pred_dir: string | null
  nasdaq_actual_change: number | null
  sp500_pred_dir: string | null
  sp500_actual_change: number | null
  dow_pred_dir: string | null
  dow_actual_change: number | null
  nvidia_pred_dir: string | null
  nvidia_actual_change: number | null
  direction_hits: number | null
  direction_total: number | null
  verified_at: string | null
  daily_accuracy: number | null
  cumulative_accuracy: number | null
}

export type Subscriber = {
  id: number
  email: string
  name: string
  active: number
  subscribed_at: string
}

export type FearGreedHistory = {
  date: string
  score: number
  rating: string
}

export type FearGreed = {
  score: number | null
  rating_en: string | null
  rating_kr: string | null
  color: string
  previous_close: number | null
  previous_1_week: number | null
  previous_1_month: number | null
  previous_1_year: number | null
  history: FearGreedHistory[]
  fetched_at: string | null
  error?: string
}

export type HedgeFundHolding = {
  name: string
  cusip: string
  value_usd: number
  shares: number
  pct: number
}

export type HedgeFund = {
  name: string
  short: string
  cik: string
  quarter: string
  report_date: string
  filed_at: string
  total_value: number
  total_value_fmt: string
  holdings_count: number
  top_holdings: HedgeFundHolding[]
}

export type HedgeFundsResponse = {
  updated_at: string
  funds: HedgeFund[]
}

async function get<T>(path: string, timeoutMs = 15000): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: 'no-store',
    headers: { 'ngrok-skip-browser-warning': 'true' },
    signal: AbortSignal.timeout(timeoutMs),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(10000),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

async function post<T>(path: string, body: unknown, headers?: Record<string, string>): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true', ...headers },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(10000),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  summary: () => get<Summary>('/api/stats/summary'),
  articles: (params?: {
    category?: string
    sentiment?: string
    min_importance?: number
    page?: number
    page_size?: number
    is_urgent?: boolean
  }) => {
    const q = new URLSearchParams()
    if (params?.category) q.set('category', params.category)
    if (params?.sentiment) q.set('sentiment', params.sentiment)
    if (params?.min_importance) q.set('min_importance', String(params.min_importance))
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.is_urgent !== undefined) q.set('is_urgent', String(params.is_urgent))
    return get<ArticlesResponse>(`/api/articles?${q}`)
  },
  articleStats: () => get<ArticleStats>('/api/articles/stats'),
  predictions: () => get<Predictions>('/api/predictions'),
  pipelineStatus: () => get<PipelineStatus>('/api/pipeline/status'),
  settings: () => get<UserSettings>('/api/settings'),
  updateSettings: (data: UserSettings) => put<UserSettings>('/api/settings', data),
  dailyTop: (day?: string) =>
    get<DailyTopResponse>(`/api/articles/daily-top${day ? `?day=${day}` : ''}`),
  dailyTopDays: () => get<{ days: string[] }>('/api/articles/daily-top/days'),
  weeklyTop: (week?: string) =>
    get<WeeklyTopResponse>(`/api/articles/weekly-top${week ? `?week=${week}` : ''}`),
  weeklyTopWeeks: () => get<{ weeks: string[] }>('/api/articles/weekly-top/weeks'),
  weeklyInsights: () => get<{ weeks: WeeklyInsight[] }>('/api/insights/weekly'),
  subscribe: (email: string, name?: string) =>
    post<{ success: boolean; email: string }>('/api/subscribe', { email, name: name ?? '' }),
  unsubscribe: (email: string) =>
    post<{ success: boolean }>('/api/unsubscribe', { email }),
  subscribers: () => get<{ subscribers: Subscriber[] }>('/api/subscribers'),
  predictionsHistory: () => get<{ records: PredictionRecord[] }>('/api/predictions/history'),
  marketCorrelation: (days?: number) =>
    get<{ data: MarketCorrelationPoint[] }>(`/api/insights/market-correlation${days ? `?days=${days}` : ''}`),
  sectorTrends: () => get<SectorTrendsResponse>('/api/insights/sector-trends'),
  relatedArticles: (market: string) =>
    get<{ articles: Article[]; market: string }>(`/api/articles/related?market=${market}`),
  runPipeline: (adminKey: string) =>
    post<{ started: boolean; pid: number }>('/api/pipeline/run', {}, { 'X-Admin-Key': adminKey }),
  fearGreed: (refresh?: boolean) =>
    get<FearGreed>(`/api/fear-greed${refresh ? '?refresh=true' : ''}`),
  reportsList: () => get<{ dates: string[]; sessions: ReportSession[] }>('/api/reports', 30000),
  latestReport: (generate?: boolean) =>
    get<Report>(`/api/reports/latest${generate ? '?generate=true' : ''}`, 30000),
  reportByDate: (date: string, runType: 'morning' | 'afternoon' = 'morning') =>
    get<Report>(`/api/reports/${date}?run_type=${runType}`, 30000),
  hedgeFunds: (force?: boolean) =>
    get<HedgeFundsResponse>(`/api/hedge-funds${force ? '?force=true' : ''}`),
}
