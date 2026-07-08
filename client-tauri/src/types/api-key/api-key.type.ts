import { SourceT } from '@/types';

export type ApiKeyT = {
  id: number;
  source: SourceT;
  name: string;
  key: string;
  secret: string;
  createdAt: string;
};