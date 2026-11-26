import { useState, useCallback } from 'react';
import { Stepper, Stack } from '@mantine/core';
import { DataSourcePanel } from './data-source-panel';
import { StrategyPanel } from './strategy-panel';
import type { StrategySchema, DataFileInfo, DataConfig } from '../../types';

interface BacktestSetupProps {
  strategies: StrategySchema[];
  dataFiles: DataFileInfo[];
  loading: boolean;
  disabled: boolean;
  onStart: (_config: Record<string, unknown>) => void;
  onOpenDataManager: () => void;
}

const DEFAULT_DATA_CONFIG: DataConfig = {
  mode: 'live',
  exchange: 'bybit',
  instrument: 'BTCUSDT',
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
  disabled,
  onStart,
  onOpenDataManager,
}: BacktestSetupProps) {
  const [activeStep, setActiveStep] = useState(0);
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
    <Stack gap="md">
      <Stepper active={activeStep} allowNextStepsSelect={false}>
        <Stepper.Step label="Data Source">
          <DataSourcePanel
            value={dataConfig}
            onChange={setDataConfig}
            dataFiles={dataFiles}
            onOpenDataManager={onOpenDataManager}
            onNext={() => setActiveStep(1)}
          />
        </Stepper.Step>
        <Stepper.Step label="Strategy">
          <StrategyPanel
            strategies={strategies}
            onStart={handleStart}
            loading={loading}
            disabled={disabled}
            onBack={() => setActiveStep(0)}
          />
        </Stepper.Step>
      </Stepper>
    </Stack>
  );
}
