import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import { ApikeyListPage } from './pages';

import '@/styles/globals.css';

import { HuiProvider } from '@/components';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Router>
      <HuiProvider>
        <Routes>
          <Route element={<ApikeyListPage />} path="/" />
          <Route element={<ApikeyListPage />} path="*" />
        </Routes>
      </HuiProvider>
    </Router>
  </React.StrictMode>,
);
