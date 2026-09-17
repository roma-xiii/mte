import type { BacktestEvent } from './types';

export interface ConnectionState {
  status: 'connecting' | 'connected' | 'disconnected';
  revision: number;
  error: string | null;
}

export interface ServerEvent {
  revision: number;
  payload: string;
}

export interface BridgeApi {
  invoke: <T>(_command: string) => Promise<T>;
  listen: <T>(_name: string, _handler: (_event: { payload: T }) => void) => Promise<() => void>;
}

// A revision belongs to one transport state. It is independent of backtest status.
export function subscribeBridge(
  api: BridgeApi,
  onConnection: (_state: ConnectionState) => void,
  onEvent: (_event: BacktestEvent) => void,
  onError: (_error: unknown) => void
) {
  let disposed = false;
  let revision = -1;
  let connected = false;
  let liveEventReceived = false;
  const cleanups: (() => void)[] = [];

  const reportError = (error: unknown, expectedRevision = revision) => {
    if (!disposed && expectedRevision === revision) onError(error);
  };

  const applyEvent = (event: ServerEvent) => {
    if (disposed || !connected || event.revision !== revision) return;
    try {
      onEvent(JSON.parse(event.payload) as BacktestEvent);
    } catch (error) {
      reportError(error);
    }
  };

  const applyConnection = (state: ConnectionState) => {
    if (disposed || state.revision <= revision) return;
    revision = state.revision;
    connected = state.status === 'connected';
    liveEventReceived = false;
    onConnection(state);
    if (!connected) return;

    // Initial server events may have preceded opening the window.
    void Promise.all([
      api.invoke('backtest_list_strategies'),
      api.invoke('backtest_list_data'),
    ]).catch((error) => reportError(error, state.revision));
  };

  const register = async <T>(name: string, handler: (_event: { payload: T }) => void) => {
    const unlisten = await api.listen<T>(name, handler);
    if (disposed) unlisten();
    else cleanups.push(unlisten);
  };

  const dispose = () => {
    disposed = true;
    cleanups.splice(0).forEach((unlisten) => unlisten());
  };

  const ready = (async () => {
    try {
      await register<ServerEvent>('backtest:event', ({ payload }) => {
        try {
          if (payload.revision === revision && connected) {
            const type = (JSON.parse(payload.payload) as BacktestEvent).type;
            if (type !== 'data_list' && type !== 'strategies_list') liveEventReceived = true;
          }
          applyEvent(payload);
        } catch (error) {
          reportError(error);
        }
      });
      if (disposed) return;
      await register<ConnectionState>('backtest:connection', ({ payload }) =>
        applyConnection(payload)
      );
      if (disposed) return;
      applyConnection(await api.invoke<ConnectionState>('backtest_get_connection'));
      if (disposed || !connected) return;
      const snapshotRevision = revision;
      const snapshot = await api.invoke<ServerEvent | null>('backtest_get_snapshot');
      // The old cached snapshot must not overwrite newer live session events.
      if (snapshot && snapshotRevision === revision && !liveEventReceived) applyEvent(snapshot);
    } catch (error) {
      reportError(error);
      dispose();
    }
  })();

  return { dispose, ready };
}
