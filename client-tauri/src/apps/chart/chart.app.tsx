import { Group } from '@mantine/core';

import { chartIntervalList } from './chart.api';
import { ChartPanel } from './chart.panel';

export const ChartApp = () => (
  <Group
    grow
    wrap="nowrap"
    align="stretch"
    h="calc(100vh - var(--mantine-spacing-md) * 2)"
    gap="md"
  >
    {chartIntervalList.map((chartInterval) => (
      <ChartPanel key={chartInterval} chartInterval={chartInterval} />
    ))}
  </Group>
);
