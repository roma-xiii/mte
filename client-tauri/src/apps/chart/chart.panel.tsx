import { Alert, Box, Loader, Stack, Text } from '@mantine/core';

import type { ChartInterval } from './chart.api';
import { chartIntervalLabelByChartInterval } from './chart.api';
import { useChart } from './chart.hook';

interface ChartPanelProps {
  chartInterval: ChartInterval;
}

export const ChartPanel = ({ chartInterval }: ChartPanelProps) => {
  const { chartContainerRef, chartLoading, chartErrorMessage } = useChart(chartInterval);

  const chartIntervalLabel = chartIntervalLabelByChartInterval[chartInterval];

  return (
    <Stack gap="xs" style={{ flex: 1, minWidth: 0, height: '100%' }}>
      {chartErrorMessage && (
        <Alert color="red" title={`Не удалось загрузить данные Binance (${chartIntervalLabel})`}>
          {chartErrorMessage}
        </Alert>
      )}
      <Box style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <Box
          ref={chartContainerRef}
          style={{
            position: 'absolute',
            inset: 0,
            visibility: chartLoading ? 'hidden' : 'visible',
          }}
        />
        <Text
          size="xs"
          c="dimmed"
          style={{ position: 'absolute', top: 8, left: 8, zIndex: 1, pointerEvents: 'none' }}
        >
          BTCUSDT {chartIntervalLabel}
        </Text>
        {chartLoading && (
          <Stack align="center" justify="center" h="100%" gap="xs">
            <Loader />
            <Text c="dimmed" size="sm">
              Загрузка BTCUSDT {chartIntervalLabel}…
            </Text>
          </Stack>
        )}
      </Box>
    </Stack>
  );
};
