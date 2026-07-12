import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { AppShell, MantineProvider } from '@mantine/core';

import '@mantine/core/styles.css';

import { BacktestApp } from './backtest.app';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <MantineProvider defaultColorScheme="dark">
        <AppShell padding="md">
          <AppShell.Main>
            <BacktestApp />
          </AppShell.Main>
        </AppShell>
      </MantineProvider>
    </BrowserRouter>
  </React.StrictMode>
);
