import { useState, useRef, useCallback, useEffect } from 'react';
import { Group, Paper, Stack, Text, Badge } from '@mantine/core';
import { Chart } from '../chart/chart';
import { ControlsPanel } from './controls-panel';
import { LogTradesPanel } from './log-trades-panel';
import type {
  BarEvent,
  EntryEvent,
  LogEvent,
  TradeEvent,
  CompleteEvent,
  PositionOpenedEvent,
} from '../../types';

interface RunningScreenProps {
  bars: BarEvent[];
  entries: EntryEvent[];
  logs: LogEvent[];
  trades: TradeEvent[];
  openPositions: PositionOpenedEvent[];
  status: string;
  progress: { current: number; total: number; pct: number } | null;
  stats: CompleteEvent['stats'] | null;
  instrument: string;
  timeframe: string;
  errorMessage: string | null;
  onSpeedChange: (_v: number) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
}

const MIN_RIGHT_WIDTH = 280;
const MAX_RIGHT_WIDTH = 600;
const DEFAULT_RIGHT_WIDTH = 340;

export function RunningScreen(props: RunningScreenProps) {
  const {
    bars,
    entries,
    logs,
    trades,
    openPositions,
    status,
    progress,
    stats,
    instrument,
    timeframe,
    errorMessage,
    onSpeedChange,
    onPause,
    onResume,
    onStop,
    onReset,
  } = props;
  const [rightWidth, setRightWidth] = useState(DEFAULT_RIGHT_WIDTH);
  const [speed, setSpeed] = useState(1);
  const dragRef = useRef(false);

  const handleSpeedChange = useCallback(
    (v: number) => {
      setSpeed(v);
      onSpeedChange(v);
    },
    [onSpeedChange]
  );

  const handleMouseDown = useCallback(() => {
    dragRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const container = document.getElementById('running-container');
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const newWidth = Math.min(MAX_RIGHT_WIDTH, Math.max(MIN_RIGHT_WIDTH, rect.right - e.clientX));
      setRightWidth(newWidth);
    };

    const handleMouseUp = () => {
      dragRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  const statusColors: Record<string, string> = {
    running: 'green',
    paused: 'yellow',
    complete: 'blue',
    error: 'red',
    starting: 'gray',
  };

  return (
    <Group
      id="running-container"
      align="stretch"
      gap={0}
      style={{ height: 'calc(100vh - 32px)', width: '100%' }}
    >
      <Paper style={{ flex: 1, minWidth: 0, position: 'relative' }} p="xs">
        <Chart
          bars={bars}
          entries={entries}
          openPositions={openPositions}
          height={window.innerHeight - 40}
        />
      </Paper>

      <div
        onMouseDown={handleMouseDown}
        style={{
          width: 4,
          cursor: 'col-resize',
          background: 'var(--mantine-color-dark-5)',
          flexShrink: 0,
        }}
      />

      <Paper style={{ width: rightWidth, flexShrink: 0 }} p="sm">
        <Stack gap="sm">
          <Group>
            <Text size="sm" fw={600}>
              {instrument}
            </Text>
            <Badge color={statusColors[status] || 'gray'} size="sm">
              {status}
            </Badge>
          </Group>
          <Text size="xs" c="dimmed">
            TF: {timeframe}
          </Text>

          <ControlsPanel
            status={status}
            progress={progress}
            speed={speed}
            errorMessage={errorMessage}
            onSpeedChange={handleSpeedChange}
            onPause={onPause}
            onResume={onResume}
            onStop={onStop}
            onReset={onReset}
          />

          {stats && (
            <Paper withBorder p="xs">
              <Text size="xs" fw={500}>
                Results
              </Text>
              <Text size="xs">PnL: {stats.pnl}</Text>
              <Text size="xs">Trades: {stats.total_trades}</Text>
              <Text size="xs">Sharpe: {stats.sharpe}</Text>
              <Text size="xs">Win Rate: {stats.win_rate}</Text>
            </Paper>
          )}

          <LogTradesPanel logs={logs} trades={trades} />
        </Stack>
      </Paper>
    </Group>
  );
}
