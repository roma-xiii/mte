import type { UTCTimestamp } from 'lightweight-charts';

export interface ChartBar {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface ChartKlineMessage {
  e: 'kline';
  k: {
    t: number;
    o: string;
    h: string;
    l: string;
    c: string;
    x: boolean;
  };
}

type ChartBarRaw = [number, string, string, string, string, ...unknown[]];

export type ChartInterval = '15m' | '1h' | '4h' | '1d';

export const chartIntervalList: ChartInterval[] = ['15m', '1h', '4h', '1d'];

export const chartIntervalLabelByChartInterval: Record<ChartInterval, string> = {
  '15m': 'M15',
  '1h': 'H1',
  '4h': 'H4',
  '1d': 'D1',
};

const chartSymbol = 'BTCUSDT';
export const chartBarLimit = 500;
const chartRestUrl = 'https://api.binance.com/api/v3/klines';

export const chartStreamUrlGet = (chartInterval: ChartInterval): string =>
  `wss://stream.binance.com/ws/${chartSymbol.toLowerCase()}@kline_${chartInterval}`;

export const chartBarListFetch = async (
  signal: AbortSignal,
  chartInterval: ChartInterval,
  barTimeEnd?: number
): Promise<ChartBar[]> => {
  const url = new URL(chartRestUrl);
  url.searchParams.set('symbol', chartSymbol);
  url.searchParams.set('interval', chartInterval);
  url.searchParams.set('limit', String(chartBarLimit));

  if (barTimeEnd !== undefined) {
    url.searchParams.set('endTime', String(barTimeEnd));
  }

  const response = await fetch(url, { signal });

  if (!response.ok) {
    throw new Error(`binance_klines_request_failed: ${response.status}`);
  }

  const barRawList = (await response.json()) as ChartBarRaw[];

  if (!Array.isArray(barRawList) || barRawList.length === 0) {
    throw new Error('binance_klines_response_empty');
  }

  return barRawList
    .map((barRaw) => ({
      time: Math.floor(barRaw[0] / 1000) as UTCTimestamp,
      open: Number(barRaw[1]),
      high: Number(barRaw[2]),
      low: Number(barRaw[3]),
      close: Number(barRaw[4]),
    }))
    .sort((barA, barB) => barA.time - barB.time);
};

export const chartKlineMessageParse = (event: MessageEvent): ChartBar | null => {
  if (typeof event.data !== 'string') {
    return null;
  }

  let message: ChartKlineMessage;

  try {
    message = JSON.parse(event.data) as ChartKlineMessage;
  } catch {
    return null;
  }

  if (message.e !== 'kline' || !message.k) {
    return null;
  }

  return {
    time: Math.floor(message.k.t / 1000) as UTCTimestamp,
    open: Number(message.k.o),
    high: Number(message.k.h),
    low: Number(message.k.l),
    close: Number(message.k.c),
  };
};
