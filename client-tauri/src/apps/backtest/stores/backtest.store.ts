import { create } from 'zustand';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface WorkerStatus {
  status: ConnectionStatus;
  error: string | null;
}

interface BacktestStore {
  workerStatus: WorkerStatus;
}

export const useBacktestStore = create<BacktestStore>(() => ({
  workerStatus: {
    status: 'disconnected',
    error: 'Error text',
  },
}));
