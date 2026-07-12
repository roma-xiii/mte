import { useEffect, useState, useCallback } from 'react';
import { Container, Loader, Center, Title } from '@mantine/core';
import { useBacktestStore } from './hooks/useBacktestStore';
import { BacktestSetup } from './components/backtest-setup/backtest-setup';
import { RunningScreen } from './components/running-screen/running-screen';
import { DataManagerModal } from './components/data-manager/data-manager-modal';

export function BacktestApp() {
  const { store, initListener, actions } = useBacktestStore();
  const [initialized, setInitialized] = useState(false);
  const [dataModalOpened, setDataModalOpened] = useState(false);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let cancelled = false;
    (async () => {
      try {
        unlisten = await initListener();
        await actions.listStrategies();
        await actions.listData();
      } catch (e) {
        console.error('Failed to initialize backtest bridge', e);
      }
      if (!cancelled) setInitialized(true);
    })();
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, [initListener]);

  const handleStart = useCallback(
    async (config: Record<string, unknown>) => {
      setStarting(true);
      try {
        await actions.start(config);
      } catch (e) {
        console.error('Failed to start backtest', e);
        actions.reset();
        setStarting(false);
        return;
      }
      setStarting(false);
    },
    [actions]
  );

  const handleStop = useCallback(async () => {
    await actions.stop();
  }, [actions]);

  const handleDeleteData = useCallback(
    async (filename: string) => {
      await actions.deleteData(filename);
      await actions.listData();
    },
    [actions]
  );

  const showSetup = store.status === 'idle';
  const showRunning = store.status !== 'idle';

  if (!initialized) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  return (
    <>
      {showSetup && (
        <Container size="xl" py="lg">
          <Title order={2} mb="lg">
            Backtest
          </Title>
          <BacktestSetup
            strategies={store.strategies}
            dataFiles={store.dataFiles}
            loading={starting}
            onStart={handleStart}
            onOpenDataManager={() => setDataModalOpened(true)}
          />
        </Container>
      )}

      {showRunning && (
        <RunningScreen
          bars={store.bars}
          entries={store.entries}
          logs={store.logs}
          trades={store.trades}
          openPositions={store.openPositions}
          status={store.status}
          progress={store.progress}
          stats={store.stats}
          instrument={store.instrument}
          timeframe={store.timeframe}
          errorMessage={store.errorMessage}
          onSpeedChange={actions.speed}
          onPause={actions.pause}
          onResume={actions.resume}
          onStop={handleStop}
          onReset={actions.reset}
        />
      )}

      <DataManagerModal
        opened={dataModalOpened}
        onClose={() => setDataModalOpened(false)}
        dataFiles={store.dataFiles}
        onDelete={handleDeleteData}
        onRefresh={actions.listData}
      />
    </>
  );
}
