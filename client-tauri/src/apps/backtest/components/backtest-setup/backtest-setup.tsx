import { Group } from '@mantine/core';
import { DataSourcePanel } from './data-source-panel';
import { StrategyPanel } from './strategy-panel';
import type { StrategySchema, DataFileInfo } from '../../types';

interface BacktestSetupProps {
  strategies: StrategySchema[];
  dataFiles: DataFileInfo[];
  loading: boolean;
  onStart: (config: Record<string, unknown>) => void;
  onOpenDataManager: () => void;
}

export function BacktestSetup({
  strategies,
  dataFiles,
  loading,
  onStart,
  onOpenDataManager,
}: BacktestSetupProps) {
  return (
    <Group align="flex-start" gap="xl" grow>
      <DataSourcePanel
        dataFiles={dataFiles}
        onOpenDataManager={onOpenDataManager}
        onConfigChange={() => {}}
      />
      <StrategyPanel strategies={strategies} onStart={onStart} loading={loading} />
    </Group>
  );
}
