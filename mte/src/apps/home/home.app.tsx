import { invoke } from '@tauri-apps/api/core';

import { Button, Stack } from '@mantine/core';

export const HomeApp = () => {
  return (
    <Stack bg="var(--mantine-color-body)" align="stretch" justify="center" gap="md">
      <Button size="xl" variant="filled" onClick={() => invoke('chart_open')}>
        Chart
      </Button>
      <Button size="xl" variant="filled" onClick={() => invoke('positions_open')}>
        Positions
      </Button>
      <Button size="xl" variant="filled" onClick={() => invoke('apikeys_open')}>
        ApiKeys
      </Button>
    </Stack>
  );
};
