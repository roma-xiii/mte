import { invoke } from '@tauri-apps/api/core';

import {
  BaseLayout,
  CenteredLayout,
  ShortcutBrick,
  ShortcutsLayout,
  KeyIcon,
  MarketIcon,
  CoinIcon,
  DealIcon,
  BookIcon,
  HistoryIcon,
  ChartIcon,
} from '@/components';

export const HomeApp = () => {
  return (
    <BaseLayout>
      <CenteredLayout>
        <ShortcutsLayout>
          <ShortcutBrick
            isDisabled
            icon={<CoinIcon />}
            label="Portfolios"
            onClick={() => invoke('portfolios_open')}
          />
          <ShortcutBrick
            isDisabled
            icon={<ChartIcon />}
            label="Watchlist"
            onClick={() => invoke('watchlist_open')}
          />
          <ShortcutBrick
            isDisabled
            icon={<DealIcon />}
            label="Positions"
            onClick={() => invoke('chart_open')}
          />
          <ShortcutBrick
            isDisabled
            icon={<MarketIcon />}
            label="Trading"
            onClick={() => invoke('trading_open')}
          />
          <ShortcutBrick
            isDisabled
            icon={<HistoryIcon />}
            label="Replay"
            onClick={() => invoke('trading_open')}
          />
          <ShortcutBrick
            isDisabled
            icon={<BookIcon />}
            label="Journal"
            onClick={() => invoke('trading_open')}
          />
          <ShortcutBrick
            icon={<KeyIcon />}
            label="Api-Keys"
            onClick={() => invoke('apikeys_open')}
          />
        </ShortcutsLayout>
      </CenteredLayout>
    </BaseLayout>
  );
};
