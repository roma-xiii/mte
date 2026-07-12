import { useEffect, useRef } from 'react';
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
} from 'lightweight-charts';
import type { ISeriesApi, LineStyle } from 'lightweight-charts';
import type { BarEvent, EntryEvent, PositionOpenedEvent } from '../../types';

interface ChartProps {
  bars: BarEvent[];
  entries: EntryEvent[];
  openPositions: PositionOpenedEvent[];
  height: number;
}

export function Chart({ bars, entries, openPositions, height }: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const markersRef = useRef<any>(null);
  const entryLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const tpLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const slLineRef = useRef<ISeriesApi<'Line'> | null>(null);
  const lastBarCount = useRef(0);
  const lastOpenPositions = useRef<PositionOpenedEvent[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#1a1b1e' },
        textColor: '#a0a0a0',
      },
      grid: {
        vertLines: { color: '#2a2b2e' },
        horzLines: { color: '#2a2b2e' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: '#2a2b2e',
      },
      timeScale: {
        borderColor: '#2a2b2e',
        timeVisible: true,
      },
      width: containerRef.current.clientWidth,
      height,
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    }) as ISeriesApi<'Candlestick'>;

    const entryLine = chart.addSeries(LineSeries, {
      color: '#eab308',
      lineStyle: 2 as LineStyle,
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
    }) as ISeriesApi<'Line'>;

    const tpLine = chart.addSeries(LineSeries, {
      color: '#22c55e',
      lineStyle: 3 as LineStyle,
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
    }) as ISeriesApi<'Line'>;

    const slLine = chart.addSeries(LineSeries, {
      color: '#ef4444',
      lineStyle: 3 as LineStyle,
      lineWidth: 1,
      lastValueVisible: false,
      priceLineVisible: false,
    }) as ISeriesApi<'Line'>;

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    entryLineRef.current = entryLine;
    tpLineRef.current = tpLine;
    slLineRef.current = slLine;
    markersRef.current = createSeriesMarkers(candleSeries);

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.resize(containerRef.current.clientWidth, height);
      }
    };

    const observer = new ResizeObserver(handleResize);
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      entryLineRef.current = null;
      tpLineRef.current = null;
      slLineRef.current = null;
      markersRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    const series = candleSeriesRef.current;
    if (!series || bars.length <= lastBarCount.current) return;

    const newBars = bars.slice(lastBarCount.current);
    for (const bar of newBars) {
      const time = Number(bar.timestamp) as any;
      series.update({
        time,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      });
    }

    if (chartRef.current && newBars.length > 0) {
      chartRef.current.timeScale().fitContent();
    }

    lastBarCount.current = bars.length;
  }, [bars]);

  useEffect(() => {
    if (!markersRef.current || entries.length === 0) return;

    markersRef.current.setMarkers(
      entries.map((e) => ({
        time: Math.floor(new Date(e.timestamp).getTime() / 1000) as any,
        position:
          e.side === 'BUY' || e.side === 'LONG' ? ('belowBar' as const) : ('aboveBar' as const),
        color: e.side === 'BUY' || e.side === 'LONG' ? '#22c55e' : '#ef4444',
        shape:
          e.side === 'BUY' || e.side === 'LONG' ? ('arrowUp' as const) : ('arrowDown' as const),
        text: `${e.side} @ ${e.price}`,
      }))
    );
  }, [entries, bars]);

  useEffect(() => {
    if (
      !candleSeriesRef.current ||
      !entryLineRef.current ||
      !tpLineRef.current ||
      !slLineRef.current
    )
      return;
    if (openPositions === lastOpenPositions.current) return;
    lastOpenPositions.current = openPositions;

    entryLineRef.current.setData([]);
    tpLineRef.current.setData([]);
    slLineRef.current.setData([]);

    const pos = openPositions[openPositions.length - 1];
    if (!pos || !bars.length) return;

    const lastTime = Number(bars[bars.length - 1].timestamp) as any;

    entryLineRef.current.setData([{ time: lastTime, value: pos.entry_price }]);

    if (pos.tp_price) {
      tpLineRef.current.setData([{ time: lastTime, value: pos.tp_price }]);
    }

    if (pos.sl_price) {
      slLineRef.current.setData([{ time: lastTime, value: pos.sl_price }]);
    }
  }, [openPositions, bars]);

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
