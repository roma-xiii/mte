import { Group, Stack, Slider, Button, Text, Progress } from '@mantine/core';

interface ControlsPanelProps {
  status: string;
  progress: { current: number; total: number; pct: number } | null;
  speed: number;
  onSpeedChange: (v: number) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

export function ControlsPanel({
  status,
  progress,
  speed,
  onSpeedChange,
  onPause,
  onResume,
  onStop,
}: ControlsPanelProps) {
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isActive = isRunning || isPaused;

  return (
    <Stack gap="sm">
      <Text size="sm" fw={500}>
        Speed: {speed}x
      </Text>
      <Slider
        min={1}
        max={100}
        step={1}
        value={speed}
        onChange={onSpeedChange}
        disabled={!isActive}
        marks={[
          { value: 1, label: '1' },
          { value: 25, label: '25' },
          { value: 50, label: '50' },
          { value: 75, label: '75' },
          { value: 100, label: '100' },
        ]}
      />

      <Group grow>
        {isRunning ? (
          <Button onClick={onPause} variant="light">
            Pause
          </Button>
        ) : isPaused ? (
          <Button onClick={onResume} variant="light" color="green">
            Resume
          </Button>
        ) : null}
        {isActive && (
          <Button onClick={onStop} color="red" variant="light">
            Stop
          </Button>
        )}
      </Group>

      {progress && (
        <>
          <Progress value={progress.pct} size="lg" />
          <Text size="sm" c="dimmed">
            {progress.current.toLocaleString()} / {progress.total.toLocaleString()} bars (
            {Math.round(progress.pct)}%)
          </Text>
        </>
      )}
    </Stack>
  );
}
