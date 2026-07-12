import { Stack, Select, TextInput, Radio, Group, Text, Button } from '@mantine/core';
import type { DataFileInfo, DataConfig } from '../../types';

interface DataSourcePanelProps {
  value: DataConfig;
  onChange: (_next: DataConfig) => void;
  dataFiles: DataFileInfo[];
  onOpenDataManager: () => void;
}

const EXCHANGES = ['bybit', 'binance'];
const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'];

export function DataSourcePanel({
  value,
  onChange,
  dataFiles,
  onOpenDataManager,
}: DataSourcePanelProps) {
  const csvOptions = dataFiles.map((f) => ({
    value: f.file,
    label: `${f.file}${f.bars ? ` (${f.bars.toLocaleString()} bars)` : ''}`,
  }));

  return (
    <Stack gap="sm">
      <Radio.Group
        value={value.mode}
        onChange={(v) => onChange({ ...value, mode: v as 'live' | 'csv' })}
        label="Data source"
      >
        <Group mt="xs">
          <Radio value="live" label="Market data" />
          <Radio value="csv" label="Use saved data" />
        </Group>
      </Radio.Group>

      {value.mode === 'live' ? (
        <>
          <Select
            label="Exchange"
            data={EXCHANGES}
            value={value.exchange}
            onChange={(v) => onChange({ ...value, exchange: v || 'bybit' })}
          />
          <TextInput
            label="Symbol"
            placeholder="EURUSD"
            value={value.instrument}
            onChange={(e) => onChange({ ...value, instrument: e.currentTarget.value })}
          />
          <Select
            label="Timeframe"
            data={TIMEFRAMES}
            value={value.timeframe}
            onChange={(v) => onChange({ ...value, timeframe: v || '1m' })}
          />
          <Radio.Group
            value={value.dateMode}
            onChange={(v) => onChange({ ...value, dateMode: v as 'dates' | 'bars' })}
          >
            <Group mt="xs">
              <Radio value="dates" label="By dates (download)" />
              <Radio value="bars" label="By bar count" />
            </Group>
          </Radio.Group>
          {value.dateMode === 'dates' ? (
            <Group grow>
              <TextInput
                label="Date from"
                type="date"
                value={value.dateFrom}
                onChange={(e) => onChange({ ...value, dateFrom: e.currentTarget.value })}
              />
              <TextInput
                label="Date to"
                type="date"
                value={value.dateTo}
                onChange={(e) => onChange({ ...value, dateTo: e.currentTarget.value })}
              />
            </Group>
          ) : (
            <TextInput
              label="Bar count"
              type="number"
              value={value.barCount}
              onChange={(e) => onChange({ ...value, barCount: Number(e.currentTarget.value) })}
            />
          )}
        </>
      ) : (
        <Stack gap="xs">
          <Select
            label="Saved data file"
            placeholder="Select a CSV file..."
            data={csvOptions}
            value={value.csvFile}
            onChange={(v) => onChange({ ...value, csvFile: v })}
            searchable
            nothingFoundMessage="No data files"
            clearable
          />
          <Button variant="subtle" size="xs" onClick={onOpenDataManager}>
            Manage data files...
          </Button>
          {value.csvFile && (
            <Text size="xs" c="dimmed">
              {(dataFiles.find((f) => f.file === value.csvFile)?.bars || 0).toLocaleString()} bars
              available
            </Text>
          )}
        </Stack>
      )}
    </Stack>
  );
}
