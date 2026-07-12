import { useRef, useEffect } from 'react';
import { Tabs, ScrollArea, Text, Table, Badge, Stack } from '@mantine/core';
import type { LogEvent, TradeEvent } from '../../types';

interface LogTradesPanelProps {
  logs: LogEvent[];
  trades: TradeEvent[];
}

function LogTab({ logs }: { logs: LogEvent[] }) {
  const viewport = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (viewport.current) {
      viewport.current.scrollTo({ top: viewport.current.scrollHeight, behavior: 'smooth' });
    }
  }, [logs.length]);

  const colorMap: Record<string, string> = {
    info: 'gray',
    warn: 'yellow',
    error: 'red',
  };

  return (
    <ScrollArea h={300} viewportRef={viewport}>
      <Stack gap={2}>
        {logs.map((log, i) => (
          <Text
            key={i}
            size="xs"
            c={colorMap[log.level] || 'gray'}
            style={{ fontFamily: 'monospace' }}
          >
            [{new Date(log.timestamp * 1000).toISOString().slice(11, 19)}] [
            {log.level.toUpperCase()}] {log.message}
          </Text>
        ))}
        {logs.length === 0 && (
          <Text size="sm" c="dimmed">
            No log entries yet
          </Text>
        )}
      </Stack>
    </ScrollArea>
  );
}

function TradesTab({ trades }: { trades: TradeEvent[] }) {
  const sorted = [...trades].sort(
    (a, b) => new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime()
  );

  return (
    <ScrollArea h={300}>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>#</Table.Th>
            <Table.Th>Side</Table.Th>
            <Table.Th>Entry</Table.Th>
            <Table.Th>Exit</Table.Th>
            <Table.Th>PnL</Table.Th>
            <Table.Th>Entry Time</Table.Th>
            <Table.Th>Exit Time</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {sorted.map((t, i) => (
            <Table.Tr key={t.id}>
              <Table.Td>{trades.length - i}</Table.Td>
              <Table.Td>
                <Badge color={t.side === 'BUY' || t.side === 'LONG' ? 'green' : 'red'} size="sm">
                  {t.side}
                </Badge>
              </Table.Td>
              <Table.Td>{t.entry_price.toFixed(2)}</Table.Td>
              <Table.Td>{t.exit_price.toFixed(2)}</Table.Td>
              <Table.Td>
                <Text c={t.pnl >= 0 ? 'green' : 'red'} fw={500}>
                  {t.pnl >= 0 ? '+' : ''}
                  {t.pnl.toFixed(2)}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="xs">{new Date(t.entry_time).toLocaleString()}</Text>
              </Table.Td>
              <Table.Td>
                <Text size="xs">{new Date(t.exit_time).toLocaleString()}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
          {trades.length === 0 && (
            <Table.Tr>
              <Table.Td colSpan={7}>
                <Text c="dimmed" ta="center">
                  No trades yet
                </Text>
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </ScrollArea>
  );
}

export function LogTradesPanel({ logs, trades }: LogTradesPanelProps) {
  return (
    <Tabs defaultValue="log">
      <Tabs.List>
        <Tabs.Tab value="log">Log ({logs.length})</Tabs.Tab>
        <Tabs.Tab value="trades">Trades ({trades.length})</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="log" pt="xs">
        <LogTab logs={logs} />
      </Tabs.Panel>
      <Tabs.Panel value="trades" pt="xs">
        <TradesTab trades={trades} />
      </Tabs.Panel>
    </Tabs>
  );
}
