import { MantineProvider } from '@mantine/core';
import '@mantine/core/styles.css';

import { ThemeProviderProps } from './theme.props';

export function ThemeProvider({ children }: ThemeProviderProps) {
  return <MantineProvider defaultColorScheme="dark">{children}</MantineProvider>;
}
