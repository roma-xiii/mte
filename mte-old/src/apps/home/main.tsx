import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { HomeApp } from './home.app';

import { HuiProvider } from '@/components';

import '@/styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <HuiProvider>
        <HomeApp />
      </HuiProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
