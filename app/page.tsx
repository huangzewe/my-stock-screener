"use client";

import {
  ArrowDownUp,
  BarChart3,
  Bell,
  Check,
  ChevronDown,
  Download,
  LineChart,
  ListFilter,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Star,
  Target,
  TrendingUp,
  X
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type Market = "US" | "TW" | "TWO" | "ETF" | "OTHER";

type Stock = {
  symbol: string;
  name: string;
  market: Market;
  industry: string;
  currency: string | null;
  price: number | null;
  change_percent: number | null;
  change_3d_percent: number | null;
  pe: number | null;
  dividend_yield: number | null;
  pbr: number | null;
  peg: number | null;
  free_cashflow_yield: number | null;
  roe: number | null;
  gross_margin: number | null;
  revenue_growth_yoy: number | null;
  eps_growth_yoy: number | null;
  debt_to_equity: number | null;
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
  is_bullish_alignment: boolean;
  alignment_gap: number | null;
  momentum_60d: number | null;
  momentum_120d: number | null;
  volume_ratio_20d: number | null;
  drawdown_1y: number | null;
  score: number;
  value_score: number | null;
  quality_growth_score: number | null;
  momentum_score: number | null;
  data_completeness: number;
  notification_streak: number;
  ranking_reasons: string[];
  risks: string[];
  tags: string[];
};

type ScreenerPayload = {
  generated_at: string;
  source: string;
  universe_size: number;
  stocks: Stock[];
};

type SortKey =
  | "score"
  | "value_score"
  | "quality_growth_score"
  | "momentum_score"
  | "data_completeness"
  | "notification_streak"
  | "change_3d_percent"
  | "change_percent"
  | "momentum_60d"
  | "volume_ratio_20d"
  | "alignment_gap"
  | "pe"
  | "roe"
  | "dividend_yield";

const presets = [
  {
    name: "多頭排列優先",
    description: "股價 > MA5 > MA20 > MA60，先確認趨勢方向。",
    filters: { bullishOnly: true, minScore: 45, maxPe: 80, minRoe: -100, minMomentum: -100, minVolumeRatio: 0 }
  },
  {
    name: "多頭 + 動能",
    description: "多頭排列之外，60 日動能也要維持正值。",
    filters: { bullishOnly: true, minScore: 50, maxPe: 80, minRoe: -100, minMomentum: 0, minVolumeRatio: 0 }
  },
  {
    name: "多頭 + 品質",
    description: "多頭排列，並要求 ROE 至少 15%。",
    filters: { bullishOnly: true, minScore: 50, maxPe: 60, minRoe: 15, minMomentum: -100, minVolumeRatio: 0 }
  }
];

export default function Home() {
  const [payload, setPayload] = useState<ScreenerPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lookupStocks, setLookupStocks] = useState<Stock[]>([]);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | Market>("ALL");
  const [industry, setIndustry] = useState("ALL");
  const [bullishOnly, setBullishOnly] = useState(false);
  const [minScore, setMinScore] = useState(0);
  const [maxPe, setMaxPe] = useState(999);
  const [minRoe, setMinRoe] = useState(-100);
  const [minMomentum, setMinMomentum] = useState(-100);
  const [minVolumeRatio, setMinVolumeRatio] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [watchlist, setWatchlist] = useState<string[]>(["2330.TW", "2454.TW", "2317.TW"]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const dataSources = [
        `https://raw.githubusercontent.com/huangzewe/my-stock-screener/main/public/data/screener-data.json?ts=${Date.now()}`,
        `/data/screener-data.json?ts=${Date.now()}`
      ];
      let latestPayload: ScreenerPayload | null = null;
      for (const source of dataSources) {
        try {
          const candidate = await fetch(source, { cache: "no-store" });
          if (candidate.ok) {
            const candidatePayload = (await candidate.json()) as ScreenerPayload;
            if (candidatePayload.universe_size >= 1000) {
              latestPayload = candidatePayload;
              break;
            }
          }
        } catch {
          // Try the packaged snapshot when the daily GitHub dataset is unavailable.
        }
      }
      if (!latestPayload) {
        throw new Error("無法讀取每日市場資料");
      }
      setPayload(latestPayload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "資料讀取失敗");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const stocks = payload?.stocks ?? [];
  const industries = useMemo(() => Array.from(new Set(stocks.map((stock) => stock.industry))).sort(), [stocks]);
  const normalizedQuery = query.trim().toLowerCase();
  const isSearchMode = normalizedQuery.length > 0;
  const searchableStocks = useMemo(() => {
    if (!isSearchMode) {
      return stocks;
    }

    const localSymbols = new Set(stocks.map((stock) => stock.symbol));
    return [...stocks, ...lookupStocks.filter((stock) => !localSymbols.has(stock.symbol))];
  }, [isSearchMode, lookupStocks, stocks]);
  const bullishCount = searchableStocks.filter((stock) => stock.is_bullish_alignment).length;

  useEffect(() => {
    if (!isSearchMode) {
      setLookupStocks([]);
      setLookupError(null);
      setLookupLoading(false);
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLookupLoading(true);
      setLookupError(null);

      try {
        const response = await fetch(`/api/lookup?q=${encodeURIComponent(query.trim())}`, {
          cache: "no-store",
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error(`即時查詢失敗：HTTP ${response.status}`);
        }
        const data = (await response.json()) as { stocks?: Stock[] };
        setLookupStocks(data.stocks ?? []);
      } catch (err) {
        if (!controller.signal.aborted) {
          setLookupError(err instanceof Error ? err.message : "即時查詢失敗");
          setLookupStocks([]);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLookupLoading(false);
        }
      }
    }, 350);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [isSearchMode, query]);

  const filtered = useMemo(() => {
    return searchableStocks
      .filter((stock) => {
        const text = `${stock.symbol} ${stock.name} ${stock.industry}`.toLowerCase();
        return (
          text.includes(normalizedQuery) &&
          (isSearchMode ||
            ((market === "ALL" || stock.market === market) &&
              (industry === "ALL" || stock.industry === industry) &&
              (!bullishOnly || stock.is_bullish_alignment) &&
              stock.score >= minScore &&
              (maxPe >= 999 || stock.pe === null || stock.pe <= maxPe) &&
              (minRoe <= -100 || (stock.roe !== null && stock.roe >= minRoe)) &&
              (minMomentum <= -100 || (stock.momentum_60d !== null && stock.momentum_60d >= minMomentum)) &&
              (minVolumeRatio <= 0 || (stock.volume_ratio_20d !== null && stock.volume_ratio_20d >= minVolumeRatio))))
        );
      })
      .sort((a, b) => {
        if (sortKey === "score") {
          const preferenceDifference = Number(isPreferredTech(b)) - Number(isPreferredTech(a));
          if (preferenceDifference !== 0) return preferenceDifference;
        }
        return numericValue(b, sortKey) - numericValue(a, sortKey);
      });
  }, [
    bullishOnly,
    industry,
    isSearchMode,
    market,
    maxPe,
    minMomentum,
    minRoe,
    minScore,
    minVolumeRatio,
    normalizedQuery,
    sortKey,
    searchableStocks
  ]);

  const averageScore =
    filtered.length === 0
      ? 0
      : Math.round(filtered.reduce((sum, stock) => sum + stock.score, 0) / filtered.length);

  const toggleWatch = (symbol: string) => {
    setWatchlist((current) =>
      current.includes(symbol) ? current.filter((item) => item !== symbol) : [...current, symbol]
    );
  };

  const applyPreset = (preset: (typeof presets)[number]) => {
    setBullishOnly(preset.filters.bullishOnly);
    setMinScore(preset.filters.minScore);
    setMaxPe(preset.filters.maxPe);
    setMinRoe(preset.filters.minRoe);
    setMinMomentum(preset.filters.minMomentum);
    setMinVolumeRatio(preset.filters.minVolumeRatio);
  };

  const exportCsv = () => {
    const header = [
      "股票代號",
      "公司名稱",
      "產業",
      "單日漲跌幅",
      "近三日漲跌幅",
      "連續入選次數",
      "總分",
      "價值分數",
      "品質成長分數",
      "動能分數",
      "資料完整度",
      "排名理由",
      "主要風險"
    ];
    const rows = filtered.map((stock) =>
      [
        stock.symbol,
        stock.name,
        stock.industry,
        `${stock.change_percent ?? ""}%`,
        `${stock.change_3d_percent ?? ""}%`,
        stock.notification_streak,
        stock.score,
        stock.value_score,
        stock.quality_growth_score,
        stock.momentum_score,
        `${stock.data_completeness}%`,
        stock.ranking_reasons.join("；"),
        stock.risks.join("；")
      ].map((value) => JSON.stringify(String(value ?? ""))).join(",")
    );
    const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "taiwan-growth-tech-screener.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <LineChart size={22} />
          </div>
          <div>
            <p>Personal Screener</p>
            <h1>我的股票篩選系統</h1>
          </div>
        </div>

        <nav className="nav-list" aria-label="主選單">
          <a className="active" href="#screener">
            <ListFilter size={18} />
            多頭篩選
          </a>
          <a href="#rules">
            <Target size={18} />
            策略模板
          </a>
          <a href="#watchlist">
            <Star size={18} />
            觀察清單
          </a>
          <a href="#alerts">
            <Bell size={18} />
            提醒條件
          </a>
        </nav>

        <section className="side-panel" id="watchlist">
          <div className="section-label">觀察清單</div>
          {watchlist.map((symbol) => {
            const stock = stocks.find((item) => item.symbol === symbol);
            return (
              <div className="watch-row" key={symbol}>
                <span>{symbol}</span>
                <strong className={(stock?.change_percent ?? 0) >= 0 ? "up" : "down"}>
                  {formatPercent(stock?.change_percent)}
                </strong>
              </div>
            );
          })}
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="search-box">
            <Search size={18} />
            <input
              aria-label="搜尋股票"
              placeholder="搜尋代號、公司或產業"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            {query && (
              <button className="icon-button" type="button" onClick={() => setQuery("")} aria-label="清除搜尋">
                <X size={16} />
              </button>
            )}
          </div>

          <div className="top-actions">
            <button className="ghost-button" type="button" onClick={() => void loadData()}>
              <RefreshCw size={16} />
              重新讀取
            </button>
            <button className="primary-button" type="button" onClick={() => setBullishOnly((value) => !value)}>
              <TrendingUp size={16} />
              {bullishOnly ? "只看多頭" : "全部股票"}
            </button>
          </div>
        </header>

        {error && <div className="status-banner">{error}</div>}
        {loading && <div className="status-banner">正在讀取台股全市場篩選資料...</div>}
        {isSearchMode && (
          <div className="status-banner">
            搜尋模式：已暫時略過所有篩選條件，並會即時查詢 Yahoo Finance 代號。
          </div>
        )}
        {lookupLoading && <div className="status-banner">正在即時查詢股票代號...</div>}
        {lookupError && <div className="status-banner">{lookupError}</div>}

        <section className="summary-grid" aria-label="篩選摘要">
          <Metric icon={<TrendingUp size={20} />} label="多頭排列" value={bullishCount.toString()} tone="teal" />
          <Metric icon={<BarChart3 size={20} />} label="符合條件" value={filtered.length.toString()} tone="blue" />
          <Metric icon={<Star size={20} />} label="平均分數" value={averageScore.toString()} tone="amber" />
          <Metric icon={<Bell size={20} />} label="股票池" value={(payload?.universe_size ?? 0).toString()} tone="rose" />
        </section>

        <section className="content-grid">
          <section className="filter-panel" id="screener">
            <div className="panel-heading">
              <div>
                <p>第一層條件</p>
                <h2>先篩選多頭排列：股價 &gt; MA5 &gt; MA20 &gt; MA60</h2>
              </div>
              <SlidersHorizontal size={20} />
            </div>

            <div className="field-grid">
              <label className="check-field">
                <input type="checkbox" checked={bullishOnly} onChange={(event) => setBullishOnly(event.target.checked)} />
                只保留多頭排列股票
              </label>

              <label>
                市場
                <span className="select-wrap">
                  <select value={market} onChange={(event) => setMarket(event.target.value as "ALL" | Market)}>
                    <option value="ALL">全部市場</option>
                    <option value="US">美股</option>
                    <option value="TW">台股上市</option>
                    <option value="TWO">台股上櫃</option>
                    <option value="ETF">ETF</option>
                  </select>
                  <ChevronDown size={16} />
                </span>
              </label>

              <label>
                產業
                <span className="select-wrap">
                  <select value={industry} onChange={(event) => setIndustry(event.target.value)}>
                    <option value="ALL">全部產業</option>
                    {industries.map((item) => (
                      <option value={item} key={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={16} />
                </span>
              </label>

              <Slider label="最低分數" value={minScore} min={0} max={100} suffix="" onChange={setMinScore} />
              <Slider label="最高本益比" value={maxPe} min={5} max={999} suffix="x" onChange={setMaxPe} />
              <Slider label="最低 ROE" value={minRoe} min={-100} max={80} suffix="%" onChange={setMinRoe} />
              <Slider label="最低 60 日動能" value={minMomentum} min={-80} max={120} suffix="%" onChange={setMinMomentum} />
              <Slider label="最低量比" value={minVolumeRatio} min={0} max={3} step={0.1} suffix="x" onChange={setMinVolumeRatio} />

              <label>
                排序
                <span className="select-wrap">
                  <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
                    <option value="score">綜合分數</option>
                    <option value="quality_growth_score">品質成長分數</option>
                    <option value="momentum_score">動能分數</option>
                    <option value="value_score">價值分數</option>
                    <option value="data_completeness">資料完整度</option>
                    <option value="notification_streak">連續入選次數</option>
                    <option value="change_3d_percent">近三日漲跌</option>
                    <option value="momentum_60d">60 日動能</option>
                    <option value="alignment_gap">股價離 MA60</option>
                    <option value="volume_ratio_20d">20 日量比</option>
                    <option value="change_percent">今日漲跌</option>
                    <option value="pe">本益比</option>
                    <option value="roe">ROE</option>
                    <option value="dividend_yield">殖利率</option>
                  </select>
                  <ArrowDownUp size={16} />
                </span>
              </label>
            </div>
          </section>

          <section className="preset-panel" id="rules">
            <div className="panel-heading compact">
              <div>
                <p>策略模板</p>
                <h2>你的選股流程</h2>
              </div>
            </div>

            <div className="rule-stack">
              <div className="rule-step active">1. 多頭排列</div>
              <div className="rule-step">2. 動能確認</div>
              <div className="rule-step">3. 品質與估值</div>
              <div className="rule-step">4. 加入觀察清單</div>
            </div>

            <div className="preset-list">
              {presets.map((preset) => (
                <button className="preset-card" key={preset.name} type="button" onClick={() => applyPreset(preset)}>
                  <span>{preset.name}</span>
                  <p>{preset.description}</p>
                </button>
              ))}
            </div>

            <div className="alert-box" id="alerts">
              <Bell size={18} />
              <p>
                每天台灣時間 22:00 更新並寄出前 50 名。連續三次以上都在寄信名單中的股票會顯示紅字，方便觀察策略訊號是否持續。
              </p>
            </div>
          </section>
        </section>

        <section className="table-shell" aria-label="股票篩選結果">
          <div className="table-toolbar">
            <div>
              <p>篩選結果</p>
              <h2>{filtered.length} 檔候選股票</h2>
              <small>資料時間：{payload ? formatDate(payload.generated_at) : "尚未載入"}</small>
            </div>
            <button className="ghost-button" type="button" onClick={exportCsv}>
              <Download size={16} />
              匯出 CSV
            </button>
          </div>

          <div className="stock-table" role="table">
            <div className="table-row table-head" role="row">
              <span>股票</span>
              <span>產業</span>
              <span>單日漲跌</span>
              <span>近三日漲跌</span>
              <span>連續入選</span>
              <span>總分</span>
              <span>價值</span>
              <span>品質成長</span>
              <span>動能</span>
              <span>完整度</span>
              <span>排名理由</span>
              <span>主要風險</span>
            </div>

            {filtered.map((stock) => (
              <div
                className={`table-row ${stock.notification_streak >= 3 ? "streak-alert-row" : ""}`}
                role="row"
                key={stock.symbol}
              >
                <div className="stock-cell">
                  <div className="stock-symbol-line">
                    <strong>{stock.symbol}</strong>
                    <button
                      className={`watch-toggle ${watchlist.includes(stock.symbol) ? "active" : ""}`}
                      type="button"
                      aria-label={`${watchlist.includes(stock.symbol) ? "移除" : "加入"}${stock.name}自選股`}
                      aria-pressed={watchlist.includes(stock.symbol)}
                      onClick={() => toggleWatch(stock.symbol)}
                    >
                      <Star size={14} fill={watchlist.includes(stock.symbol) ? "currentColor" : "none"} />
                    </button>
                  </div>
                  <small>{stock.name}</small>
                  <div className="tag-row">
                    {stock.tags.map((tag) => (
                      <span className="tag" key={`${stock.symbol}-${tag}`}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <span>{stock.industry}</span>
                <span className={(stock.change_percent ?? 0) >= 0 ? "up" : "down"}>
                  {formatPercent(stock.change_percent)}
                </span>
                <span className={(stock.change_3d_percent ?? 0) >= 0 ? "up" : "down"}>
                  {formatPercent(stock.change_3d_percent)}
                </span>
                <strong className={stock.notification_streak >= 3 ? "streak-alert" : ""}>
                  {stock.notification_streak > 0 ? `${stock.notification_streak} 次` : "—"}
                </strong>
                <strong>{stock.score.toFixed(1)}</strong>
                <span>{formatNumber(stock.value_score)}</span>
                <span>{formatNumber(stock.quality_growth_score)}</span>
                <span>{formatNumber(stock.momentum_score)}</span>
                <span>{formatPercent(stock.data_completeness)}</span>
                <small className="reason-cell">{stock.ranking_reasons.join("、")}</small>
                <small className={stock.risks.length ? "risk-cell" : "reason-cell"}>
                  {stock.risks.length ? stock.risks.join("、") : "—"}
                </small>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function numericValue(stock: Stock, key: SortKey) {
  return stock[key] ?? -999;
}

function isPreferredTech(stock: Stock) {
  return [
    "半導體業",
    "電腦及週邊設備業",
    "電子零組件業",
    "其他電子業",
    "通信網路業",
    "資訊服務業",
    "數位雲端",
    "光電業"
  ].includes(stock.industry);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return value.toLocaleString("zh-TW", { maximumFractionDigits: 2 });
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

function formatRatio(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toFixed(2)}x`;
}

function formatPrice(stock: Stock) {
  if (stock.price === null) return "-";
  const prefix = stock.currency === "TWD" ? "NT$" : stock.currency === "USD" ? "$" : "";
  return `${prefix}${stock.price.toLocaleString("zh-TW", { maximumFractionDigits: 2 })}`;
}

function Metric({
  icon,
  label,
  value,
  tone
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: "teal" | "blue" | "amber" | "rose";
}) {
  return (
    <article className={`metric metric-${tone}`}>
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <label>
      <span className="slider-label">
        {label}
        <strong>
          {value}
          {suffix}
        </strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
