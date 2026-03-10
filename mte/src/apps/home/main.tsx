import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { AppShell, MantineProvider } from '@mantine/core';

import '@mantine/core/styles.css';

import { HomeApp } from './home.app';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <MantineProvider defaultColorScheme="dark">
        <AppShell
          padding="md"
          // header={{ height: 60 }}
        >
          {/* <AppShell.Header>
          head
        </AppShell.Header> */}
          <AppShell.Main>
            <HomeApp />
          </AppShell.Main>
        </AppShell>
      </MantineProvider>
    </BrowserRouter>
  </React.StrictMode>
);
