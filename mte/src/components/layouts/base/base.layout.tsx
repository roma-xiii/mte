import { AppShell } from '@mantine/core';
import { BaseProps } from './base.props';

export const BaseLayout = ({ header, children }: BaseProps) => {
  return (
    <AppShell padding="md" header={{ height: header ? 60 : 0 }}>
      {header && <AppShell.Header>{header}</AppShell.Header>}
      <AppShell.Main>{children}</AppShell.Main>
    </AppShell>
  );
};
