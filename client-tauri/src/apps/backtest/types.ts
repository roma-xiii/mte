export interface BarEvent {
  type: 'bar';
  index: number;
  total: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
  balance: number;
}

export interface TradeEvent {
  type: 'trade';
  id: string;
  side: string;
  instrument_id: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  pnl: number;
  entry_time: string;
  exit_time: string;
}

export interface EntryEvent {
  type: 'entry';
  side: string;
  price: number;
  size: number;
  timestamp: string;
}

export interface ExitEvent {
  type: 'exit';
  side: string;
  price: number;
  pnl: number;
  timestamp: string;
}

export interface LogEvent {
  type: 'log';
  level: 'info' | 'warn' | 'error';
  message: string;
  timestamp: number;
}

export interface ReadyEvent {
  type: 'ready';
  total_bars: number;
  instrument: string;
  timeframe: string;
}

export interface CompleteEvent {
  type: 'complete';
  stats: {
    pnl: string;
    total_trades: number;
    sharpe: string;
    max_drawdown: string;
    win_rate: string;
  };
}

export interface ProgressEvent {
  type: 'progress';
  current: number;
  total: number;
  pct: number;
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export interface PausedEvent {
  type: 'paused';
}

export interface SnapshotEvent {
  type: 'snapshot';
  bars: BarEvent[];
  trades: TradeEvent[];
  entries: EntryEvent[];
  exits: ExitEvent[];
  logs: LogEvent[];
  ready?: { total_bars: number; instrument: string; timeframe: string };
  complete?: CompleteEvent;
  error?: { message: string };
}

export interface DataListEvent {
  type: 'data_list';
  data: DataFileInfo[];
}

export interface StrategiesListEvent {
  type: 'strategies_list';
  data: StrategySchema[];
}

export interface PositionOpenedEvent {
  type: 'position_opened';
  id: string;
  side: string;
  instrument_id: string;
  quantity: number;
  entry_price: number;
  timestamp: string;
  tp_price?: number;
  sl_price?: number;
}

export interface StrategyParam {
  type: 'int' | 'float' | 'select' | 'bool' | 'string';
  label: string;
  default: number | string | boolean;
  min?: number;
  max?: number;
  options?: string[];
}

export interface StrategySchema {
  name: string;
  label: string;
  params: Record<string, StrategyParam>;
}

export interface DataFileInfo {
  file: string;
  instrument: string;
  timeframe: string;
  bars?: number;
  date_from?: string;
  date_to?: string;
}

export type BacktestEvent =
  | BarEvent
  | TradeEvent
  | EntryEvent
  | ExitEvent
  | LogEvent
  | ReadyEvent
  | CompleteEvent
  | ProgressEvent
  | ErrorEvent
  | PausedEvent
  | SnapshotEvent
  | DataListEvent
  | StrategiesListEvent
  | PositionOpenedEvent;

export interface DataConfig {
  mode: 'live' | 'csv';
  exchange: string;
  instrument: string;
  timeframe: string;
  dateMode: 'dates' | 'bars';
  dateFrom: string;
  dateTo: string;
  barCount: number;
  csvFile: string | null;
}

export type BacktestStatus =
  | 'idle'
  | 'starting'
  | 'running'
  | 'paused'
  | 'complete'
  | 'error';
