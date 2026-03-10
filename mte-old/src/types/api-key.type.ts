export type ApiKeyT = {
  id: number;
  source: 'bybit' | 'binance';
  key: string;
  secret: string;
  description?: string;
};
