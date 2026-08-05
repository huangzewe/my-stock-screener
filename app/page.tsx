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
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Star,
  Target,
  TrendingUp,
  X
} from "lucide-react";
import { useMemo, useState } from "react";

type Market = "US" | "TW" | "ETF";
type Stock = {
  symbol: string;
  name: string;
  market: Market;
  sector: string;
  price: number;
  change: number;
  pe: number;
  epsGrowth: number;
  revenueGrowth: number;
  grossMargin: number;
  roe: number;
  dividendYield: number;
  debtRatio: number;
  momentum: number;
  volumeRatio: number;
  score: number;
  tags: string[];
};

type SortKey = keyof Pick<
  Stock,
  | "score"
  | "change"
  | "pe"
  | "epsGrowth"
  | "revenueGrowth"
  | "roe"
  | "dividendYield"
  | "momentum"
>;

const stocks: Stock[] = [
  {
    symbol: "NVDA",
    name: "NVIDIA",
    market: "US",
    sector: "AI 半導體",
    price: 178.42,
    change: 2.4,
    pe: 38.6,
    epsGrowth: 45,
    revenueGrowth: 62,
    grossMargin: 74,
    roe: 91,
    dividendYield: 0.02,
    debtRatio: 17,
    momentum: 86,
    volumeRatio: 1.4,
    score: 94,
    tags: ["成長", "大型股", "高動能"]
  },
  {
    symbol: "TSM",
    name: "台積電 ADR",
    market: "US",
    sector: "晶圓代工",
    price: 238.15,
    change: 1.1,
    pe: 27.2,
    epsGrowth: 28,
    revenueGrowth: 33,
    grossMargin: 58,
    roe: 31,
    dividendYield: 1.1,
    debtRatio: 24,
    momentum: 78,
    volumeRatio: 1.1,
    score: 89,
    tags: ["品質", "AI 供應鏈"]
  },
  {
    symbol: "2330",
    name: "台積電",
    market: "TW",
    sector: "半導體",
    price: 1295,
    change: 0.7,
    pe: 25.8,
    epsGrowth: 25,
    revenueGrowth: 30,
    grossMargin: 57,
    roe: 30,
    dividendYield: 1.3,
    debtRatio: 22,
    momentum: 72,
    volumeRatio: 0.9,
    score: 87,
    tags: ["權值", "品質"]
  },
  {
    symbol: "AAPL",
    name: "Apple",
    market: "US",
    sector: "消費電子",
    price: 229.31,
    change: -0.4,
    pe: 31.3,
    epsGrowth: 8,
    revenueGrowth: 5,
    grossMargin: 46,
    roe: 136,
    dividendYield: 0.4,
    debtRatio: 31,
    momentum: 54,
    volumeRatio: 0.8,
    score: 71,
    tags: ["大型股", "品牌"]
  },
  {
    symbol: "MSFT",
    name: "Microsoft",
    market: "US",
    sector: "雲端軟體",
    price: 514.26,
    change: 0.9,
    pe: 34.1,
    epsGrowth: 17,
    revenueGrowth: 15,
    grossMargin: 69,
    roe: 35,
    dividendYield: 0.6,
    debtRatio: 18,
    momentum: 69,
    volumeRatio: 1,
    score: 84,
    tags: ["品質", "AI 軟體"]
  },
  {
    symbol: "0050",
    name: "元大台灣50",
    market: "ETF",
    sector: "台股 ETF",
    price: 205.75,
    change: 0.3,
    pe: 21.5,
    epsGrowth: 13,
    revenueGrowth: 12,
    grossMargin: 49,
    roe: 20,
    dividendYield: 2.4,
    debtRatio: 12,
    momentum: 61,
    volumeRatio: 0.7,
    score: 76,
    tags: ["ETF", "核心配置"]
  },
  {
    symbol: "UNH",
    name: "UnitedHealth",
    market: "US",
    sector: "醫療保險",
    price: 548.12,
    change: 1.8,
    pe: 18.4,
    epsGrowth: 12,
    revenueGrowth: 9,
    grossMargin: 24,
    roe: 24,
    dividendYield: 1.5,
    debtRatio: 37,
    momentum: 67,
    volumeRatio: 1.3,
    score: 80,
    tags: ["價值", "防禦"]
  },
  {
    symbol: "AMZN",
    name: "Amazon",
    market: "US",
    sector: "電商雲端",
    price: 224.88,
    change: 1.6,
    pe: 36.9,
    epsGrowth: 31,
    revenueGrowth: 14,
    grossMargin: 49,
    roe: 23,
    dividendYield: 0,
    debtRatio: 29,
    momentum: 75,
    volumeRatio: 1.2,
    score: 83,
    tags: ["成長", "雲端"]
  },
  {
    symbol: "2317",
    name: "鴻海",
    market: "TW",
    sector: "電子代工",
    price: 183.5,
    change: -1.2,
    pe: 15.7,
    epsGrowth: 11,
    revenueGrowth: 8,
    grossMargin: 6,
    roe: 10,
    dividendYield: 3.2,
    debtRatio: 42,
    momentum: 48,
    volumeRatio: 1.6,
    score: 62,
    tags: ["價值", "AI 伺服器"]
  },
  {
    symbol: "GOOGL",
    name: "Alphabet",
    market: "US",
    sector: "搜尋與雲端",
    price: 196.04,
    change: 0.5,
    pe: 24.6,
    epsGrowth: 18,
    revenueGrowth: 13,
    grossMargin: 58,
    roe: 32,
    dividendYield: 0.4,
    debtRatio: 8,
    momentum: 64,
    volumeRatio: 0.9,
    score: 82,
    tags: ["品質", "合理估值"]
  }
];

const sectors = Array.from(new Set(stocks.map((stock) => stock.sector)));

const presets = [
  {
    name: "成長動能",
    description: "營收與 EPS 成長明顯，股價動能偏強。",
    filters: { minScore: 78, maxPe: 45, minRevenueGrowth: 14, minRoe: 18, minMomentum: 65 }
  },
  {
    name: "穩健品質",
    description: "ROE、毛利率與負債結構較漂亮。",
    filters: { minScore: 75, maxPe: 35, minRevenueGrowth: 8, minRoe: 22, minMomentum: 50 }
  },
  {
    name: "價值股息",
    description: "估值較低，且有較好的現金殖利率。",
    filters: { minScore: 55, maxPe: 22, minRevenueGrowth: 0, minRoe: 8, minMomentum: 35 }
  }
];

export default function Home() {
  const [query, setQuery] = useState("");
  const [market, setMarket] = useState<"ALL" | Market>("ALL");
  const [sector, setSector] = useState("ALL");
  const [minScore, setMinScore] = useState(70);
  const [maxPe, setMaxPe] = useState(40);
  const [minRevenueGrowth, setMinRevenueGrowth] = useState(8);
  const [minRoe, setMinRoe] = useState(12);
  const [minMomentum, setMinMomentum] = useState(50);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [watchlist, setWatchlist] = useState<string[]>(["TSM", "2330", "MSFT"]);

  const filtered = useMemo(() => {
    return stocks
      .filter((stock) => {
        const text = `${stock.symbol} ${stock.name} ${stock.sector}`.toLowerCase();
        return (
          text.includes(query.toLowerCase()) &&
          (market === "ALL" || stock.market === market) &&
          (sector === "ALL" || stock.sector === sector) &&
          stock.score >= minScore &&
          stock.pe <= maxPe &&
          stock.revenueGrowth >= minRevenueGrowth &&
          stock.roe >= minRoe &&
          stock.momentum >= minMomentum
        );
      })
      .sort((a, b) => b[sortKey] - a[sortKey]);
  }, [market, maxPe, minMomentum, minRevenueGrowth, minRoe, minScore, query, sector, sortKey]);

  const averageScore =
    filtered.length === 0
      ? 0
      : Math.round(filtered.reduce((sum, stock) => sum + stock.score, 0) / filtered.length);

  const toggleWatch = (symbol: string) => {
    setWatchlist((current) =>
      current.includes(symbol)
        ? current.filter((item) => item !== symbol)
        : [...current, symbol]
    );
  };

  const applyPreset = (preset: (typeof presets)[number]) => {
    setMinScore(preset.filters.minScore);
    setMaxPe(preset.filters.maxPe);
    setMinRevenueGrowth(preset.filters.minRevenueGrowth);
    setMinRoe(preset.filters.minRoe);
    setMinMomentum(preset.filters.minMomentum);
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
            篩選器
          </a>
          <a href="#watchlist">
            <Star size={18} />
            觀察清單
          </a>
          <a href="#rules">
            <Target size={18} />
            策略模板
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
            if (!stock) return null;
            return (
              <div className="watch-row" key={symbol}>
                <span>{symbol}</span>
                <strong className={stock.change >= 0 ? "up" : "down"}>
                  {stock.change >= 0 ? "+" : ""}
                  {stock.change}%
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
            <button className="ghost-button" type="button">
              <RefreshCw size={16} />
              更新資料
            </button>
            <button className="primary-button" type="button">
              <Plus size={16} />
              新策略
            </button>
          </div>
        </header>

        <section className="summary-grid" aria-label="篩選摘要">
          <Metric icon={<BarChart3 size={20} />} label="符合股票" value={filtered.length.toString()} tone="teal" />
          <Metric icon={<TrendingUp size={20} />} label="平均分數" value={averageScore.toString()} tone="blue" />
          <Metric icon={<Star size={20} />} label="觀察中" value={watchlist.length.toString()} tone="amber" />
          <Metric icon={<Bell size={20} />} label="啟用提醒" value="4" tone="rose" />
        </section>

        <section className="content-grid">
          <section className="filter-panel" id="screener">
            <div className="panel-heading">
              <div>
                <p>篩選條件</p>
                <h2>把你的投資偏好變成規則</h2>
              </div>
              <SlidersHorizontal size={20} />
            </div>

            <div className="field-grid">
              <label>
                市場
                <span className="select-wrap">
                  <select value={market} onChange={(event) => setMarket(event.target.value as "ALL" | Market)}>
                    <option value="ALL">全部市場</option>
                    <option value="US">美股</option>
                    <option value="TW">台股</option>
                    <option value="ETF">ETF</option>
                  </select>
                  <ChevronDown size={16} />
                </span>
              </label>

              <label>
                產業
                <span className="select-wrap">
                  <select value={sector} onChange={(event) => setSector(event.target.value)}>
                    <option value="ALL">全部產業</option>
                    {sectors.map((item) => (
                      <option value={item} key={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={16} />
                </span>
              </label>

              <Slider label="最低分數" value={minScore} min={0} max={100} suffix="" onChange={setMinScore} />
              <Slider label="最高本益比" value={maxPe} min={5} max={60} suffix="x" onChange={setMaxPe} />
              <Slider
                label="最低營收成長"
                value={minRevenueGrowth}
                min={-10}
                max={70}
                suffix="%"
                onChange={setMinRevenueGrowth}
              />
              <Slider label="最低 ROE" value={minRoe} min={0} max={60} suffix="%" onChange={setMinRoe} />
              <Slider label="最低動能" value={minMomentum} min={0} max={100} suffix="" onChange={setMinMomentum} />

              <label>
                排序
                <span className="select-wrap">
                  <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}>
                    <option value="score">綜合分數</option>
                    <option value="change">今日漲跌</option>
                    <option value="pe">本益比</option>
                    <option value="epsGrowth">EPS 成長</option>
                    <option value="revenueGrowth">營收成長</option>
                    <option value="roe">ROE</option>
                    <option value="dividendYield">殖利率</option>
                    <option value="momentum">動能</option>
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
                <h2>快速套用常用篩選</h2>
              </div>
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
              <p>當股票通過目前條件、跌破動能門檻或估值進入甜蜜區時，可在下一版接上 Email/LINE/Slack 提醒。</p>
            </div>
          </section>
        </section>

        <section className="table-shell" aria-label="股票篩選結果">
          <div className="table-toolbar">
            <div>
              <p>篩選結果</p>
              <h2>{filtered.length} 檔候選股票</h2>
            </div>
            <button className="ghost-button" type="button">
              <Download size={16} />
              匯出 CSV
            </button>
          </div>

          <div className="stock-table" role="table">
            <div className="table-row table-head" role="row">
              <span>股票</span>
              <span>價格</span>
              <span>漲跌</span>
              <span>本益比</span>
              <span>營收</span>
              <span>ROE</span>
              <span>動能</span>
              <span>分數</span>
              <span>追蹤</span>
            </div>

            {filtered.map((stock) => (
              <div className="table-row" role="row" key={stock.symbol}>
                <div className="stock-cell">
                  <strong>{stock.symbol}</strong>
                  <small>
                    {stock.name} · {stock.sector}
                  </small>
                </div>
                <span>{stock.market === "TW" || stock.market === "ETF" ? "NT$" : "$"}{stock.price.toLocaleString()}</span>
                <span className={stock.change >= 0 ? "up" : "down"}>
                  {stock.change >= 0 ? "+" : ""}
                  {stock.change}%
                </span>
                <span>{stock.pe}x</span>
                <span>{stock.revenueGrowth}%</span>
                <span>{stock.roe}%</span>
                <span>
                  <span className="momentum">
                    <i style={{ width: `${stock.momentum}%` }} />
                  </span>
                </span>
                <strong>{stock.score}</strong>
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
  suffix,
  onChange
}: {
  label: string;
  value: number;
  min: number;
  max: number;
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
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
