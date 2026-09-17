import { useState, useRef, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { subscribeBridge } from '../bridge';
import type { ConnectionState } from '../bridge';
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
  connection: ConnectionState;
  commandError: string | null;
  strategiesLoaded: boolean;
  dataLoaded: boolean;
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
    connection: { status: 'connecting', revision: -1, error: null },
    commandError: null,
    strategiesLoaded: false,
    dataLoaded: false,
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
    const next = { ...storeRef.current, ...partial };
    storeRef.current = next;
    setStore(next);
  }, []);

  const handleEvent = useCallback(
    (event: BacktestEvent) => {
      switch (event.type) {
        case 'strategies_list':
          update({ strategies: event.data, strategiesLoaded: true });
          break;
        case 'data_list':
          update({ dataFiles: event.data, dataLoaded: true });
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

  const reportCommandError = useCallback(
    (error: unknown) =>
      update({ commandError: error instanceof Error ? error.message : String(error) }),
    [update]
  );

  const initListener = useCallback(
    () =>
      subscribeBridge(
        { invoke, listen },
        (connection) =>
          update({
            connection,
            strategies: [],
            dataFiles: [],
            strategiesLoaded: false,
            dataLoaded: false,
            commandError: null,
          }),
        handleEvent,
        reportCommandError
      ),
    [handleEvent, reportCommandError, update]
  );

  const actions = useMemo(() => {
    const command = async (name: string, args?: Record<string, unknown>) => {
      const revision = storeRef.current.connection.revision;
      try {
        update({ commandError: null });
        if (storeRef.current.connection.status !== 'connected') {
          throw new Error('Нет подключения к Python. Дождитесь восстановления соединения.');
        }
        await invoke(name, args);
        return true;
      } catch (error) {
        if (revision === storeRef.current.connection.revision) reportCommandError(error);
        return false;
      }
    };
    return {
      start: async (config: Record<string, unknown>) => {
        if (
          !storeRef.current.strategiesLoaded ||
          !storeRef.current.strategies.some((strategy) => strategy.name === config.strategy_name)
        ) {
          reportCommandError('Выберите доступную стратегию.');
          return;
        }
        update({ status: 'starting' });
        const sent = await command('backtest_start', { config: JSON.stringify(config) });
        // A failed send must not issue Stop or erase an existing session.
        if (!sent && storeRef.current.status === 'starting') update({ status: 'idle' });
      },
      pause: () => command('backtest_pause'),
      resume: () => command('backtest_resume'),
      stop: () => command('backtest_stop'),
      speed: (value: number) => command('backtest_speed', { value }),
      listData: () => command('backtest_list_data'),
      listStrategies: () => command('backtest_list_strategies'),
      deleteData: (filename: string) => command('backtest_delete_data', { filename }),
      dismissError: () => update({ commandError: null }),
      reset: async () => {
        try {
          await invoke('backtest_clear_snapshot');
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
            commandError: null,
          });
        } catch (error) {
          reportCommandError(error);
        }
      },
    };
  }, [reportCommandError, update]);

  return { store, initListener, actions };
}
