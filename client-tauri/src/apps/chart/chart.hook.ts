import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

import { CandlestickSeries, createChart } from 'lightweight-charts';
import type { LogicalRange } from 'lightweight-charts';

import {
  chartBarLimit,
  chartBarListFetch,
  chartKlineMessageParse,
  chartStreamUrlGet,
} from './chart.api';
import type { ChartBar, ChartInterval } from './chart.api';

export interface ChartHookResult {
  chartContainerRef: RefObject<HTMLDivElement | null>;
  chartLoading: boolean;
  chartErrorMessage: string | null;
}

const chartRequestTimeout = 15000;
const chartOlderRetryDelay = 5000;
const chartOlderThreshold = 10;

export const useChart = (chartInterval: ChartInterval): ChartHookResult => {
  const [chartLoading, setChartLoading] = useState(true);
  const [chartErrorMessage, setChartErrorMessage] = useState<string | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const barListRef = useRef<ChartBar[]>([]);
  const barTimeFirstRef = useRef<number | null>(null);
  const hasOlderRef = useRef(true);
  const isLoadingOlderRef = useRef(false);
  const isUserInteractedRef = useRef(false);
  const olderAbortControllerRef = useRef<AbortController | null>(null);
  const olderRetryTimeRef = useRef(0);

  useEffect(() => {
    const chartContainer = chartContainerRef.current;

    if (!chartContainer) {
      return;
    }

    let isCancelled = false;
    let socket: WebSocket | null = null;
    const abortController = new AbortController();
    const timeoutId = setTimeout(() => abortController.abort(), chartRequestTimeout);

    const chart = createChart(chartContainer, {
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
        timeVisible: chartInterval !== '1d',
        secondsVisible: false,
      },
      width: chartContainer.clientWidth,
      height: chartContainer.clientHeight,
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    });

    const resizeObserver = new ResizeObserver(() => {
      chart.resize(chartContainer.clientWidth, chartContainer.clientHeight);
    });
    resizeObserver.observe(chartContainer);

    const handleUserInteraction = () => {
      isUserInteractedRef.current = true;
    };

    chartContainer.addEventListener('wheel', handleUserInteraction, { passive: true });
    chartContainer.addEventListener('pointerdown', handleUserInteraction);

    const chartBarListOlderLoad = async () => {
      const barTimeFirst = barTimeFirstRef.current;

      if (isLoadingOlderRef.current || !hasOlderRef.current || barTimeFirst === null) {
        return;
      }

      if (Date.now() < olderRetryTimeRef.current) {
        return;
      }

      isLoadingOlderRef.current = true;

      const olderAbortController = new AbortController();
      olderAbortControllerRef.current = olderAbortController;
      const olderTimeoutId = setTimeout(() => olderAbortController.abort(), chartRequestTimeout);

      try {
        const barListOlder = await chartBarListFetch(
          olderAbortController.signal,
          chartInterval,
          barTimeFirst * 1000 - 1
        );

        if (isCancelled) {
          return;
        }

        if (barListOlder.length === 0) {
          hasOlderRef.current = false;
          return;
        }

        const barListCurrent = barListRef.current;
        const barTimeSet = new Set(barListCurrent.map((bar) => bar.time));
        const barListOlderNew = barListOlder.filter((bar) => !barTimeSet.has(bar.time));

        if (barListOlderNew.length === 0) {
          hasOlderRef.current = false;
          return;
        }

        const logicalRange = chart.timeScale().getVisibleLogicalRange();
        const barListMerged = [...barListOlderNew, ...barListCurrent];

        candleSeries.setData(barListMerged);

        if (logicalRange) {
          chart.timeScale().setVisibleLogicalRange({
            from: logicalRange.from + barListOlderNew.length,
            to: logicalRange.to + barListOlderNew.length,
          });
        }

        barListRef.current = barListMerged;
        barTimeFirstRef.current = barListMerged[0].time;

        if (barListOlder.length < chartBarLimit) {
          hasOlderRef.current = false;
        }

        setChartErrorMessage(null);
      } catch (error) {
        if (isCancelled) {
          return;
        }

        olderRetryTimeRef.current = Date.now() + chartOlderRetryDelay;

        if (olderAbortController.signal.aborted) {
          setChartErrorMessage('binance_klines_request_timeout');
          return;
        }

        setChartErrorMessage(
          error instanceof Error ? error.message : 'binance_klines_request_failed'
        );
      } finally {
        clearTimeout(olderTimeoutId);

        if (olderAbortControllerRef.current === olderAbortController) {
          olderAbortControllerRef.current = null;
        }

        isLoadingOlderRef.current = false;
      }
    };

    const handleVisibleLogicalRangeChange = (logicalRange: LogicalRange | null) => {
      if (!logicalRange || !isUserInteractedRef.current) {
        return;
      }

      if (logicalRange.from < chartOlderThreshold) {
        chartBarListOlderLoad();
      }
    };

    const chartLoad = async () => {
      try {
        const barList = await chartBarListFetch(abortController.signal, chartInterval);

        clearTimeout(timeoutId);

        if (isCancelled) {
          return;
        }

        barListRef.current = barList;
        barTimeFirstRef.current = barList[0]?.time ?? null;

        candleSeries.setData(barList);
        chart.timeScale().fitContent();
        chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange);

        setChartLoading(false);
        setChartErrorMessage(null);

        socket = new WebSocket(chartStreamUrlGet(chartInterval));

        socket.onmessage = (event) => {
          const bar = chartKlineMessageParse(event);

          if (!bar) {
            return;
          }

          const barList = barListRef.current;
          const barLast = barList[barList.length - 1];

          if (barLast && barLast.time === bar.time) {
            barList[barList.length - 1] = bar;
          } else if (!barLast || bar.time > barLast.time) {
            barList.push(bar);
          }

          candleSeries.update(bar);
        };

        socket.onerror = () => {
          if (!isCancelled) {
            setChartErrorMessage('binance_stream_connection_failed');
          }
        };
      } catch (error) {
        clearTimeout(timeoutId);

        if (isCancelled) {
          return;
        }

        setChartLoading(false);

        if (abortController.signal.aborted) {
          setChartErrorMessage('binance_klines_request_timeout');
          return;
        }

        setChartErrorMessage(
          error instanceof Error ? error.message : 'binance_klines_request_failed'
        );
      }
    };

    chartLoad();

    return () => {
      isCancelled = true;
      clearTimeout(timeoutId);
      abortController.abort();
      olderAbortControllerRef.current?.abort();
      olderAbortControllerRef.current = null;
      socket?.close();
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange);
      chartContainer.removeEventListener('wheel', handleUserInteraction);
      chartContainer.removeEventListener('pointerdown', handleUserInteraction);
      resizeObserver.disconnect();
      chart.remove();
      barListRef.current = [];
      barTimeFirstRef.current = null;
      hasOlderRef.current = true;
      isLoadingOlderRef.current = false;
      isUserInteractedRef.current = false;
      olderRetryTimeRef.current = 0;
    };
  }, [chartInterval]);

  return { chartContainerRef, chartLoading, chartErrorMessage };
};
