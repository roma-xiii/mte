import { useState, useRef, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import type {
  BacktestEvent,
  BacktestStatus,
  BarEvent,
  TradeEvent,
  EntryEvent,
  ExitEvent,
  LogEvent,
  StrategySchema,
  DataFileInfo,
  CompleteEvent,
  PositionOpenedEvent,
} from '../types';

export interface BacktestStore {
  status: BacktestStatus;
  strategies: StrategySchema[];
  dataFiles: DataFileInfo[];
  bars: BarEvent[];
  trades: TradeEvent[];
  entries: EntryEvent[];
  exits: ExitEvent[];
  logs: LogEvent[];
  openPositions: PositionOpenedEvent[];
  progress: { current: number; total: number; pct: number } | null;
  stats: CompleteEvent['stats'] | null;
  instrument: string;
  timeframe: string;
  totalBars: number;
  errorMessage: string | null;
}

export function useBacktestStore() {
  const [store, setStore] = useState<BacktestStore>({
    status: 'idle',
    strategies: [],
    dataFiles: [],
    bars: [],
    trades: [],
    entries: [],
    exits: [],
    logs: [],
    openPositions: [],
    progress: null,
    stats: null,
    instrument: '',
    timeframe: '',
    totalBars: 0,
    errorMessage: null,
  });

  const storeRef = useRef(store);
  storeRef.current = store;

  const update = useCallback((partial: Partial<BacktestStore>) => {
    setStore((prev) => {
      const next = { ...prev, ...partial };
      storeRef.current = next;
      return next;
    });
  }, []);

  const handleEvent = useCallback(
    (event: BacktestEvent) => {
      switch (event.type) {
        case 'strategies_list':
          update({ strategies: event.data });
          break;
        case 'data_list':
          update({ dataFiles: event.data });
          break;
        case 'ready':
          update({
            status: 'running',
            instrument: event.instrument,
            timeframe: event.timeframe,
            totalBars: event.total_bars,
            bars: [],
            trades: [],
            logs: [],
            entries: [],
            exits: [],
            openPositions: [],
            progress: null,
            stats: null,
            errorMessage: null,
          });
          break;
        case 'bar':
          update({ bars: [...storeRef.current.bars, event] });
          break;
        case 'trade':
          update({ trades: [...storeRef.current.trades, event] });
          break;
        case 'entry':
          update({ entries: [...storeRef.current.entries, event] });
          break;
        case 'exit':
          update({ exits: [...storeRef.current.exits, event] });
          break;
        case 'log':
          update({ logs: [...storeRef.current.logs.slice(-1000), event] });
          break;
        case 'position_opened':
          update({ openPositions: [...storeRef.current.openPositions, event] });
          break;
        case 'progress':
          update({ progress: event });
          break;
        case 'paused':
          update({ status: 'paused' });
          break;
        case 'complete':
          update({
            status: 'complete',
            stats: event.stats,
            progress: {
              current: storeRef.current.totalBars,
              total: storeRef.current.totalBars,
              pct: 100,
            },
          });
          break;
        case 'error':
          update({ status: 'error', errorMessage: (event as any).message || 'Unknown error' });
          break;
        case 'snapshot': {
          const s = event;
          update({
            bars: s.bars || [],
            trades: s.trades || [],
            entries: s.entries || [],
            exits: s.exits || [],
            logs: s.logs || [],
            status: s.complete ? 'complete' : s.error ? 'error' : s.ready ? 'running' : 'idle',
            stats: s.complete?.stats || null,
            instrument: s.ready?.instrument || '',
            timeframe: s.ready?.timeframe || '',
            totalBars: s.ready?.total_bars || 0,
            errorMessage: s.error?.message || null,
          });
          break;
        }
      }
    },
    [update]
  );

  const initListener = useCallback(async () => {
    const unlisten = await listen<string>('backtest:event', (event) => {
      try {
        const data = JSON.parse(event.payload) as BacktestEvent;
        handleEvent(data);
      } catch {
        /* ignore parse errors */
      }
    });

    const snapshot = await invoke<string | null>('backtest_get_snapshot');
    if (snapshot) {
      try {
        handleEvent(JSON.parse(snapshot) as BacktestEvent);
      } catch {
        /* ignore */
      }
    }

    return unlisten;
  }, [handleEvent]);

  const actions = useMemo(
    () => ({
      start: (config: Record<string, unknown>) => {
        update({ status: 'starting' });
        const p = invoke('backtest_start', { config: JSON.stringify(config) });
        const timeout = new Promise((_, reject) =>
          setTimeout(() => reject(new Error('backtest_start invoke timeout')), 5000)
        );
        return Promise.race([p, timeout]);
      },
      pause: () => invoke('backtest_pause'),
      resume: () => invoke('backtest_resume'),
      stop: () => invoke('backtest_stop'),
      speed: (value: number) => invoke('backtest_speed', { value }),
      listData: () => invoke('backtest_list_data'),
      listStrategies: () => invoke('backtest_list_strategies'),
      deleteData: (filename: string) => invoke('backtest_delete_data', { filename }),
      reset: () => {
        invoke('backtest_stop').catch(() => {});
        invoke('backtest_clear_snapshot').catch(() => {});
        update({
          status: 'idle',
          bars: [],
          trades: [],
          entries: [],
          exits: [],
          logs: [],
          openPositions: [],
          progress: null,
          stats: null,
          instrument: '',
          timeframe: '',
          totalBars: 0,
          errorMessage: null,
        });
      },
    }),
    []
  );

  return { store, initListener, actions };
}
