import { useEffect, useState, useCallback } from 'react';
import { Alert, Badge, Container, Group, Loader, Center, Stack, Text, Title } from '@mantine/core';
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
    let cancelled = false;
    const subscription = initListener();
    void subscription.ready.then(() => {
      if (!cancelled) setInitialized(true);
    });
    return () => {
      cancelled = true;
      subscription.dispose();
    };
  }, [initListener]);

  const handleStart = useCallback(
    async (config: Record<string, unknown>) => {
      setStarting(true);
      try {
        await actions.start(config);
      } finally {
        setStarting(false);
      }
    },
    [actions]
  );

  const handleStop = useCallback(async () => {
    await actions.stop();
  }, [actions]);

  const handleDeleteData = useCallback(
    async (filename: string) => {
      if (await actions.deleteData(filename)) await actions.listData();
    },
    [actions]
  );

  const connected = store.connection.status === 'connected';
  const catalogsLoaded = store.strategiesLoaded && store.dataLoaded;

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
    <Stack gap="sm">
      <Group justify="space-between">
        <Badge color={connected ? 'green' : 'yellow'}>
          {connected
            ? 'Python подключён'
            : store.connection.status === 'connecting'
              ? 'Подключение к Python…'
              : 'Нет подключения к Python'}
        </Badge>
        {connected && !catalogsLoaded && <Text size="sm">Загрузка стратегий и данных…</Text>}
      </Group>
      {!connected && (
        <Alert color="yellow" title="Сервер тестера недоступен">
          Запустите Python-сервер командой make run в каталоге nautilus. Подключение восстановится
          автоматически.
          {store.connection.error && (
            <Text size="xs" mt="xs">
              {store.connection.error}
            </Text>
          )}
        </Alert>
      )}
      {store.commandError && (
        <Alert
          color="red"
          title="Не удалось выполнить действие"
          withCloseButton
          onClose={actions.dismissError}
        >
          {store.commandError}
        </Alert>
      )}
      {connected && store.strategiesLoaded && store.strategies.length === 0 && (
        <Alert color="yellow">Сервер не вернул доступных стратегий. Проверьте журнал Python.</Alert>
      )}
      {showSetup && (
        <Container size="xl" py="lg">
          <Title order={2} mb="lg">
            Backtest
          </Title>
          <BacktestSetup
            strategies={store.strategies}
            dataFiles={store.dataFiles}
            loading={starting}
            disabled={!connected || !catalogsLoaded}
            onStart={handleStart}
            onOpenDataManager={() => setDataModalOpened(true)}
          />
        </Container>
      )}

      {showRunning && (
        <RunningScreen
          connected={connected}
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
        connected={connected}
        opened={dataModalOpened}
        onClose={() => setDataModalOpened(false)}
        dataFiles={store.dataFiles}
        onDelete={handleDeleteData}
        onRefresh={actions.listData}
      />
    </Stack>
  );
}
