import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import { ApiKeyListPage, ApiKeyCreatePage } from './pages';
import { ThemeProvider } from '@/components';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <Router>
        <Routes>
          <Route element={<ApiKeyListPage />} path="/" />
          <Route element={<ApiKeyCreatePage />} path="/create" />
          <Route element={<ApiKeyListPage />} path="*" />
        </Routes>
      </Router>
    </ThemeProvider>
  </React.StrictMode>
);
