import { useEffect, useRef } from 'react';
import { createChart, createSeriesMarkers, CandlestickSeries } from 'lightweight-charts';
import type { ISeriesApi } from 'lightweight-charts';
import type { BarEvent, EntryEvent } from '../../types';

interface ChartProps {
  bars: BarEvent[];
  entries: EntryEvent[];
  height: number;
}

export function Chart({ bars, entries, height }: ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const markersRef = useRef<any>(null);
  const lastBarCount = useRef(0);

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

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
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

  return <div ref={containerRef} style={{ width: '100%', height }} />;
}
