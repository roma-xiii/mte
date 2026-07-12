import { useState } from 'react';
import { Select, TextInput, Stack, Radio, Group, Text, Button } from '@mantine/core';
import type { DataFileInfo } from '../../types';

interface DataSourcePanelProps {
  dataFiles: DataFileInfo[];
  onOpenDataManager: () => void;
  onConfigChange: (partial: Record<string, unknown>) => void;
}

const EXCHANGES = ['bybit', 'binance'];
const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];

export function DataSourcePanel({
  dataFiles,
  onOpenDataManager,
  onConfigChange,
}: DataSourcePanelProps) {
  const [mode, setMode] = useState<'live' | 'csv'>('live');
  const [exchange, setExchange] = useState('bybit');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [timeframe, setTimeframe] = useState('1m');
  const [dateMode, setDateMode] = useState<'dates' | 'bars'>('dates');
  const [dateFrom, setDateFrom] = useState('2024-01-01');
  const [dateTo, setDateTo] = useState('2024-06-01');
  const [barCount, setBarCount] = useState(5000);
  const [selectedCsv, setSelectedCsv] = useState<string | null>(null);

  const handleModeChange = (v: string) => {
    setMode(v as 'live' | 'csv');
    if (v === 'csv') {
      onConfigChange({ csv_file: selectedCsv, synthetic: false });
    }
  };

  const handleCsvChange = (v: string | null) => {
    setSelectedCsv(v);
    if (v) {
      onConfigChange({ csv_file: v, synthetic: false });
    }
  };

  const csvOptions = dataFiles.map((f) => ({
    value: f.file,
    label: `${f.file}${f.bars ? ` (${f.bars.toLocaleString()} bars)` : ''}`,
  }));

  return (
    <Stack gap="sm">
      <Radio.Group value={mode} onChange={handleModeChange} label="Data source">
        <Group mt="xs">
          <Radio value="live" label="Download from exchange" />
          <Radio value="csv" label="Use saved data" />
        </Group>
      </Radio.Group>

      {mode === 'live' ? (
        <>
          <Select
            label="Exchange"
            data={EXCHANGES}
            value={exchange}
            onChange={(v) => {
              setExchange(v || 'bybit');
              onConfigChange({ exchange: v });
            }}
          />
          <TextInput
            label="Symbol"
            placeholder="BTCUSDT"
            value={symbol}
            onChange={(e) => {
              setSymbol(e.currentTarget.value);
              onConfigChange({ instrument: e.currentTarget.value });
            }}
          />
          <Select
            label="Timeframe"
            data={TIMEFRAMES}
            value={timeframe}
            onChange={(v) => {
              setTimeframe(v || '1m');
              onConfigChange({ timeframe: v });
            }}
          />
          <Radio.Group value={dateMode} onChange={(v) => setDateMode(v as 'dates' | 'bars')}>
            <Group mt="xs">
              <Radio value="dates" label="By dates" />
              <Radio value="bars" label="By bar count" />
            </Group>
          </Radio.Group>
          {dateMode === 'dates' ? (
            <Group grow>
              <TextInput
                label="Date from"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.currentTarget.value);
                  onConfigChange({ date_from: e.currentTarget.value });
                }}
              />
              <TextInput
                label="Date to"
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.currentTarget.value);
                  onConfigChange({ date_to: e.currentTarget.value });
                }}
              />
            </Group>
          ) : (
            <TextInput
              label="Bar count"
              type="number"
              value={barCount}
              onChange={(e) => {
                setBarCount(Number(e.currentTarget.value));
                onConfigChange({ synthetic_bars: Number(e.currentTarget.value) });
              }}
            />
          )}
        </>
      ) : (
        <Stack gap="xs">
          <Select
            label="Saved data file"
            placeholder="Select a CSV file..."
            data={csvOptions}
            value={selectedCsv}
            onChange={handleCsvChange}
            searchable
            nothingFoundMessage="No data files"
            clearable
          />
          <Button variant="subtle" size="xs" onClick={onOpenDataManager}>
            Manage data files...
          </Button>
          {selectedCsv && (
            <Text size="xs" c="dimmed">
              {(dataFiles.find((f) => f.file === selectedCsv)?.bars || 0).toLocaleString()} bars
              available
            </Text>
          )}
        </Stack>
      )}
    </Stack>
  );
}
