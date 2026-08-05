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
  pe: number | null;
  dividend_yield: number | null;
  pbr: number | null;
  roe: number | null;
  gross_margin: number | null;
  debt_to_equity: number | null;
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
  is_bullish_alignment: boolean;
  alignment_gap: number | null;
  momentum_60d: number | null;
  volume_ratio_20d: number | null;
  drawdown_1y: number | null;
  score: number;
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
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | Market>("ALL");
  const [industry, setIndustry] = useState("ALL");
  const [bullishOnly, setBullishOnly] = useState(true);
  const [minScore, setMinScore] = useState(45);
  const [maxPe, setMaxPe] = useState(80);
  const [minRoe, setMinRoe] = useState(-100);
  const [minMomentum, setMinMomentum] = useState(-100);
  const [minVolumeRatio, setMinVolumeRatio] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [watchlist, setWatchlist] = useState<string[]>(["2330.TW", "MSFT", "NVDA"]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/data/screener-data.json?ts=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`資料讀取失敗：HTTP ${response.status}`);
      }
      setPayload((await response.json()) as ScreenerPayload);
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
  const bullishCount = stocks.filter((stock) => stock.is_bullish_alignment).length;
  const normalizedQuery = query.trim().toLowerCase();
  const isSearchMode = normalizedQuery.length > 0;

  const filtered = useMemo(() => {
    return stocks
      .filter((stock) => {
        const text = `${stock.symbol} ${stock.name} ${stock.industry}`.toLowerCase();
        return (
          text.includes(normalizedQuery) &&
          (market === "ALL" || stock.market === market) &&
          (industry === "ALL" || stock.industry === industry) &&
          (isSearchMode ||
            ((!bullishOnly || stock.is_bullish_alignment) &&
              stock.score >= minScore &&
              (stock.pe === null || stock.pe <= maxPe) &&
              (stock.roe ?? -999) >= minRoe &&
              (stock.momentum_60d ?? -999) >= minMomentum &&
              (stock.volume_ratio_20d ?? 0) >= minVolumeRatio))
        );
      })
      .sort((a, b) => numericValue(b, sortKey) - numericValue(a, sortKey));
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
    stocks
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
    const header = ["symbol", "name", "market", "industry", "price", "ma5", "ma20", "ma60", "momentum_60d", "score"];
    const rows = filtered.map((stock) =>
      header.map((key) => JSON.stringify(String(stock[key as keyof Stock] ?? ""))).join(",")
    );
    const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "bullish-screener.csv";
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
        {loading && <div className="status-banner">正在讀取 yfinance 篩選資料...</div>}
        {isSearchMode && (
          <div className="status-banner">
            搜尋模式：已暫時略過多頭排列、分數、PE、ROE、動能與量比條件，顯示股票池中的相符股票。
          </div>
        )}

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
              <Slider label="最高本益比" value={maxPe} min={5} max={120} suffix="x" onChange={setMaxPe} />
              <Slider label="最低 ROE" value={minRoe} min={-100} max={80} suffix="%" onChange={setMinRoe} />
              <Slider label="最低 60 日動能" value={minMomentum} min={-80} max={120} suffix="%" onChange={setMinMomentum} />
              <Slider label="最低量比" value={minVolumeRatio} min={0} max={3} step={0.1} suffix="x" onChange={setMinVolumeRatio} />

              <label>
                排序
                <span className="select-wrap">
                  <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
                    <option value="score">綜合分數</option>
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
                目前是盤後資料篩選。下一步可以加入排程，讓 Python 每天收盤後更新 JSON，網站自動顯示最新多頭排列名單。
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
              <span>價格</span>
              <span>漲跌</span>
              <span>均線排列</span>
              <span>動能</span>
              <span>量比</span>
              <span>PE / ROE</span>
              <span>分數</span>
              <span>追蹤</span>
            </div>

            {filtered.map((stock) => (
              <div className="table-row" role="row" key={stock.symbol}>
                <div className="stock-cell">
                  <strong>{stock.symbol}</strong>
                  <small>
                    {stock.name} · {stock.industry}
                  </small>
                  <div className="tag-row">
                    {stock.tags.map((tag) => (
                      <span className="tag" key={`${stock.symbol}-${tag}`}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
                <span>{formatPrice(stock)}</span>
                <span className={(stock.change_percent ?? 0) >= 0 ? "up" : "down"}>{formatPercent(stock.change_percent)}</span>
                <div className="ma-stack">
                  <strong className={stock.is_bullish_alignment ? "up" : "down"}>
                    {stock.is_bullish_alignment ? "多頭" : "未成立"}
                  </strong>
                  <small>
                    {formatNumber(stock.ma5)} / {formatNumber(stock.ma20)} / {formatNumber(stock.ma60)}
                  </small>
                </div>
                <span>{formatPercent(stock.momentum_60d)}</span>
                <span>{formatRatio(stock.volume_ratio_20d)}</span>
                <span>
                  {formatNumber(stock.pe)}x / {formatPercent(stock.roe)}
                </span>
                <strong>{stock.score.toFixed(1)}</strong>
                <button
                  className={`star-button ${watchlist.includes(stock.symbol) ? "selected" : ""}`}
                  type="button"
                  onClick={() => toggleWatch(stock.symbol)}
                  aria-label={watchlist.includes(stock.symbol) ? `移除 ${stock.symbol}` : `追蹤 ${stock.symbol}`}
                >
                  {watchlist.includes(stock.symbol) ? <Check size={16} /> : <Star size={16} />}
                </button>
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
