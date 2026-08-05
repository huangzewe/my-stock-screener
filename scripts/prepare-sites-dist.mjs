import { copyFileSync, cpSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const distDir = join(process.cwd(), "dist");
const clientDir = join(distDir, "client");
const hostingSource = join(process.cwd(), ".openai", "hosting.json");
const hostingTarget = join(distDir, ".openai", "hosting.json");
const workerTarget = join(distDir, "server", "index.js");

mkdirSync(clientDir, { recursive: true });
mkdirSync(dirname(hostingTarget), { recursive: true });
mkdirSync(dirname(workerTarget), { recursive: true });

for (const entry of readdirSync(distDir, { withFileTypes: true })) {
  if ([".openai", "client", "server"].includes(entry.name)) {
    continue;
  }

  cpSync(join(distDir, entry.name), join(clientDir, entry.name), { recursive: true });
}

copyFileSync(hostingSource, hostingTarget);

writeFileSync(
  workerTarget,
  `export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const acceptsHtml = request.headers.get("accept")?.includes("text/html");

    if (url.pathname === "/api/lookup") {
      return lookupStocks(url);
    }

    if (url.pathname === "/") {
      url.pathname = "/index.html";
    }

    let response = await env.ASSETS.fetch(new Request(url, request));

    if (response.status === 404 && acceptsHtml) {
      url.pathname = "/index.html";
      response = await env.ASSETS.fetch(new Request(url, request));
    }

    return response;
  }
};

async function lookupStocks(url) {
  const query = (url.searchParams.get("q") || "").trim();
  if (!query || query.length < 2) {
    return json({ stocks: [] });
  }

  const candidates = await findSymbols(query);
  const stocks = [];

  for (const candidate of candidates.slice(0, 6)) {
    try {
      const stock = await buildStock(candidate);
      if (stock) {
        stocks.push(stock);
      }
    } catch (error) {
      console.warn("lookup failed", candidate.symbol, error?.message || error);
    }
  }

  return json({ stocks });
}

async function findSymbols(query) {
  const normalized = query.toUpperCase();
  const symbols = [];

  if (/^[0-9]{4}$/.test(normalized)) {
    symbols.push({ symbol: normalized + ".TW", name: normalized, market: "TW", industry: "Yahoo Finance" });
    symbols.push({ symbol: normalized + ".TWO", name: normalized, market: "TWO", industry: "Yahoo Finance" });
  } else if (/^[A-Z.]{1,12}$/.test(normalized)) {
    symbols.push({ symbol: normalized, name: normalized, market: inferMarket(normalized), industry: "Yahoo Finance" });
  }

  const searchUrl = "https://query2.finance.yahoo.com/v1/finance/search?q=" +
    encodeURIComponent(query) +
    "&quotesCount=8&newsCount=0";
  const response = await fetch(searchUrl, {
    headers: {
      "accept": "application/json",
      "user-agent": "Mozilla/5.0"
    }
  });

  if (response.ok) {
    const payload = await response.json();
    for (const quote of payload.quotes || []) {
      if (!["EQUITY", "ETF"].includes(quote.quoteType)) {
        continue;
      }
      symbols.push({
        symbol: quote.symbol,
        name: quote.longname || quote.shortname || quote.symbol,
        market: inferMarket(quote.symbol),
        industry: quote.industryDisp || quote.industry || quote.sectorDisp || "Yahoo Finance"
      });
    }
  }

  const seen = new Set();
  return symbols.filter((item) => {
    if (seen.has(item.symbol)) {
      return false;
    }
    seen.add(item.symbol);
    return true;
  });
}

async function buildStock(candidate) {
  const chartUrl = "https://query1.finance.yahoo.com/v8/finance/chart/" +
    encodeURIComponent(candidate.symbol) +
    "?range=6mo&interval=1d";
  const response = await fetch(chartUrl, {
    headers: {
      "accept": "application/json",
      "user-agent": "Mozilla/5.0"
    }
  });

  if (!response.ok) {
    return null;
  }

  const payload = await response.json();
  const result = payload.chart?.result?.[0];
  const quote = result?.indicators?.quote?.[0];
  const closes = compactNumbers(quote?.close);
  const volumes = compactNumbers(quote?.volume);
  const meta = result?.meta || {};

  if (!closes.length) {
    return null;
  }

  const price = last(closes);
  const previous = closes.length > 1 ? closes[closes.length - 2] : null;
  const ma5 = average(closes.slice(-5));
  const ma20 = average(closes.slice(-20));
  const ma60 = average(closes.slice(-60));
  const start60 = closes.length >= 60 ? closes[closes.length - 60] : null;
  const avgVolume20 = average(volumes.slice(-20));
  const lastVolume = last(volumes);
  const high = Math.max(...closes);

  const changePercent = previous ? ((price - previous) / previous) * 100 : null;
  const momentum60d = start60 ? ((price - start60) / start60) * 100 : null;
  const volumeRatio = avgVolume20 && lastVolume ? lastVolume / avgVolume20 : null;
  const drawdown = high ? ((price - high) / high) * 100 : null;
  const bullish = Boolean(price && ma5 && ma20 && ma60 && price > ma5 && ma5 > ma20 && ma20 > ma60);
  const alignmentGap = ma60 ? ((price - ma60) / ma60) * 100 : null;
  const score = scoreLookup({ bullish, momentum60d, volumeRatio, drawdown, alignmentGap });
  const tags = ["即時查詢"];

  if (bullish) tags.unshift("多頭排列");
  if ((momentum60d || 0) >= 15) tags.push("動能");

  return {
    symbol: meta.symbol || candidate.symbol,
    name: meta.longName || meta.shortName || candidate.name || candidate.symbol,
    market: candidate.market,
    industry: candidate.industry,
    currency: meta.currency || null,
    price: round(price),
    change_percent: round(changePercent),
    pe: null,
    dividend_yield: null,
    pbr: null,
    roe: null,
    gross_margin: null,
    debt_to_equity: null,
    ma5: round(ma5),
    ma20: round(ma20),
    ma60: round(ma60),
    is_bullish_alignment: bullish,
    alignment_gap: round(alignmentGap),
    momentum_60d: round(momentum60d),
    volume_ratio_20d: round(volumeRatio),
    drawdown_1y: round(drawdown),
    score,
    tags
  };
}

function scoreLookup(values) {
  let score = values.bullish ? 55 : 25;
  score += clamp(((values.momentum60d || 0) + 20) / 60, 0, 1) * 25;
  score += clamp(((values.volumeRatio || 0) - 0.5) / 1.7, 0, 1) * 10;
  score += clamp(((values.alignmentGap || 0) + 10) / 35, 0, 1) * 10;
  return round(Math.min(score, 100));
}

function compactNumbers(values) {
  return (values || []).filter((value) => typeof value === "number" && Number.isFinite(value));
}

function average(values) {
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function last(values) {
  return values.length ? values[values.length - 1] : null;
}

function round(value) {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  return Math.round(value * 100) / 100;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function inferMarket(symbol) {
  if (symbol.endsWith(".TW")) return "TW";
  if (symbol.endsWith(".TWO")) return "TWO";
  if (symbol.endsWith(".HK") || symbol.endsWith(".T") || symbol.endsWith(".SR")) return "OTHER";
  return "US";
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store"
    }
  });
}
`,
  "utf8"
);
