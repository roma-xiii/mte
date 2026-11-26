import { useBacktestStore } from '@/apps/backtest/stores';
import { Badge } from '@mantine/core';
import React from 'react';

export const ConnectionStatusFeature = () => {
  const workerStatus = useBacktestStore((s) => s.workerStatus);
  const color =
    workerStatus.status === 'connected'
      ? 'green'
      : workerStatus.status === 'connecting'
        ? 'orange'
        : 'red';

  return (
    <React.Fragment>
      <Badge style={{ position: 'absolute', right: '14px', bottom: '14px' }} color={color}>
        {workerStatus.status}
      </Badge>
      {/* {workerStatus.status === 'disconnected' && workerStatus.error !== null && (
        <Alert color="red" title="Worker is not available">
          {workerStatus.error}
        </Alert>
      )} */}
    </React.Fragment>
  );
};
