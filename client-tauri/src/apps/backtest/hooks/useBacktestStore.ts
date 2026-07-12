import { useState, useRef, useCallback } from 'react';
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
  progress: { current: number; total: number; pct: number } | null;
  stats: CompleteEvent['stats'] | null;
  instrument: string;
  timeframe: string;
  totalBars: number;
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
    progress: null,
    stats: null,
    instrument: '',
    timeframe: '',
    totalBars: 0,
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
            progress: null,
            stats: null,
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
          update({ status: 'error' });
          break;
        case 'snapshot': {
          const s = event;
          update({
            bars: s.bars || [],
            trades: s.trades || [],
            entries: s.entries || [],
            exits: s.exits || [],
            logs: s.logs || [],
            status: s.complete ? 'complete' : s.ready ? 'running' : 'idle',
            stats: s.complete?.stats || null,
            instrument: s.ready?.instrument || '',
            timeframe: s.ready?.timeframe || '',
            totalBars: s.ready?.total_bars || 0,
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

  const actions = {
    start: useCallback(
      (config: Record<string, unknown>) => {
        update({ status: 'starting' });
        return invoke('backtest_start', { config: JSON.stringify(config) });
      },
      [update]
    ),

    pause: useCallback(() => invoke('backtest_pause'), []),
    resume: useCallback(() => invoke('backtest_resume'), []),
    stop: useCallback(() => invoke('backtest_stop'), []),
    speed: useCallback((value: number) => invoke('backtest_speed', { value }), []),
    listData: useCallback(() => invoke('backtest_list_data'), []),
    listStrategies: useCallback(() => invoke('backtest_list_strategies'), []),
    deleteData: useCallback((filename: string) => invoke('backtest_delete_data', { filename }), []),
  };

  return { store, initListener, actions };
}
