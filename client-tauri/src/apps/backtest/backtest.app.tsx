import { useCallback, useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Button, Stack, Code, Group, Text, Progress } from '@mantine/core';

type Event = Record<string, string | number | boolean>;

export const BacktestApp = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [status, setStatus] = useState('Idle');
  const [progress, setProgress] = useState(0);
  const [totalBars, setTotalBars] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      invoke('backtest_stop');
    };
  }, []);

  const wsSend = useCallback((msg: object) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
    }
  }, []);

  const start = async () => {
    wsRef.current?.close();
    setLogs([]);
    setProgress(0);
    setTotalBars(0);
    setStatus('Starting...');

    try {
      const url = await invoke<string>('backtest_start');
      setLogs((prev) => [...prev, `WS: ${url}`]);

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => setLogs((prev) => [...prev, 'WS: connected']);

      ws.onmessage = (event) => {
        const evt: Event = JSON.parse(event.data);
        const t = evt.type as string;

        setLogs((prev) => [...prev.slice(-500), event.data]);

        if (t === 'ready') {
          setTotalBars(evt.total_bars as number);
          setStatus('Running');
          wsSend({ cmd: 'next', n: 1 });
        } else if (t === 'bar') {
          setProgress((((evt.index as number) + 1) / totalBars) * 100);
        } else if (t === 'complete') {
          setStatus('Complete');
          setProgress(100);
        } else if (t === 'paused') {
          setStatus('Paused');
        } else if (t === 'error') {
          setStatus('Error');
          setLogs((prev) => [...prev, `ERROR: ${evt.message}`]);
        }
      };

      ws.onclose = () => {
        wsRef.current = null;
        setStatus((prev) => (prev === 'Stopped' ? prev : 'Idle'));
      };

      ws.onerror = () => {
        setStatus('Error');
        setLogs((prev) => [...prev, 'WS: error']);
      };
    } catch (err) {
      setStatus('Error');
      setLogs((prev) => [...prev, `Start failed: ${err}`]);
    }
  };

  const stop = () => {
    wsSend({ cmd: 'stop' });
    wsRef.current?.close();
    wsRef.current = null;
    invoke('backtest_stop');
    setStatus('Stopped');
  };

  const pause = () => wsSend({ cmd: 'pause' });
  const resume = () => wsSend({ cmd: 'resume' });
  const sendNext = (n: number) => wsSend({ cmd: 'next', n });

  return (
    <Stack>
      <Group>
        <Text fw={700}>Status: {status}</Text>
        {totalBars > 0 && (
          <Progress value={progress} size="sm" w={200} />
        )}
      </Group>

      <Group>
        <Button onClick={start}>Start</Button>
        <Button onClick={() => sendNext(10)}>Next 10</Button>
        <Button onClick={() => sendNext(100)}>Next 100</Button>
        <Button onClick={pause}>Pause</Button>
        <Button onClick={resume}>Resume</Button>
        <Button color="red" onClick={stop}>
          Stop
        </Button>
      </Group>

      <Code block style={{ height: 'calc(100vh - 180px)', overflow: 'auto', fontSize: 12 }}>
        {logs.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </Code>
    </Stack>
  );
};
