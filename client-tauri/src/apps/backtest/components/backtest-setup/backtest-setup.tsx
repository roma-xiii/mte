import { useState, useCallback } from 'react';
import { Group } from '@mantine/core';
import { DataSourcePanel } from './data-source-panel';
import { StrategyPanel } from './strategy-panel';
import type { StrategySchema, DataFileInfo, DataConfig } from '../../types';

interface BacktestSetupProps {
  strategies: StrategySchema[];
  dataFiles: DataFileInfo[];
  loading: boolean;
  onStart: (_config: Record<string, unknown>) => void;
  onOpenDataManager: () => void;
}

const DEFAULT_DATA_CONFIG: DataConfig = {
  mode: 'live',
  exchange: 'bybit',
  instrument: 'EURUSD',
  timeframe: '1m',
  dateMode: 'bars',
  dateFrom: '',
  dateTo: '',
  barCount: 2000,
  csvFile: null,
};

export function BacktestSetup({
  strategies,
  dataFiles,
  loading,
  onStart,
  onOpenDataManager,
}: BacktestSetupProps) {
  const [dataConfig, setDataConfig] = useState<DataConfig>(DEFAULT_DATA_CONFIG);

  const handleStart = useCallback(
    (strategyConfig: Record<string, unknown>) => {
      const config: Record<string, unknown> = { ...strategyConfig };

      if (dataConfig.mode === 'csv') {
        config.csv_file = dataConfig.csvFile;
        config.timeframe = dataConfig.timeframe;
      } else if (dataConfig.dateMode === 'dates') {
        config.exchange = dataConfig.exchange;
        config.instrument = dataConfig.instrument;
        config.timeframe = dataConfig.timeframe;
        config.date_from = dataConfig.dateFrom;
        config.date_to = dataConfig.dateTo;
      } else {
        config.exchange = dataConfig.exchange;
        config.instrument = dataConfig.instrument;
        config.timeframe = dataConfig.timeframe;
        config.synthetic_bars = dataConfig.barCount;
      }

      onStart(config);
    },
    [dataConfig, onStart]
  );

  return (
    <Group align="flex-start" gap="xl" grow>
      <DataSourcePanel
        value={dataConfig}
        onChange={setDataConfig}
        dataFiles={dataFiles}
        onOpenDataManager={onOpenDataManager}
      />
      <StrategyPanel strategies={strategies} onStart={handleStart} loading={loading} />
    </Group>
  );
}
