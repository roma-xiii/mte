import React from 'react';
import { ApiKeyT, SourceT } from '@/types';

const elements = [
  {
    id: 1,
    source: 'Bybit Spot' as SourceT,
    name: 'My trading key 1',
    key: '1cPcYmt9uZMVUnx49E',
    secret: '*****gRsh',
    createdAt: '12.01.2026',
  },
  {
    id: 2,
    source: 'Bybit Futures' as SourceT,
    name: 'My trading key 2',
    key: '1cPcYmt9uZMVUnx49E',
    secret: '*****gRsh',
    createdAt: '12.01.2026',
  },
  {
    id: 3,
    source: 'Bybit Spot' as SourceT,
    name: 'My trading key 3',
    key: '1cPcYmt9uZMVUnx49E',
    secret: '*****gRsh',
    createdAt: '12.01.2026',
  },
  {
    id: 4,
    source: 'Bybit Futures' as SourceT,
    name: 'My trading key 4',
    key: '1cPcYmt9uZMVUnx49E',
    secret: '*****gRsh',
    createdAt: '12.01.2026',
  },
  {
    id: 5,
    source: 'Bybit Spot' as SourceT,
    name: 'My trading key 5',
    key: '1cPcYmt9uZMVUnx49E',
    secret: '*****gRsh',
    createdAt: '12.01.2026',
  },
];

export interface MainContextInterface {
  apiKeyList: ApiKeyT[];
}

export const useMainHook = (): MainContextInterface => {
  const [apiKeyList, setApiKeyList] = React.useState<ApiKeyT[]>([]);

  React.useEffect(() => {
    const fetchApiKeyList = async () => {
      setApiKeyList(elements);
    };
    fetchApiKeyList();
  }, []);

  return React.useMemo(() => ({ apiKeyList }), [apiKeyList]);
};
