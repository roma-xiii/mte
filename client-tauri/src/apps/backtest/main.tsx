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

// import React from 'react';
// import ReactDOM from 'react-dom/client';
// import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// import { ThemeProvider } from '@/components';
// import { BacktestSetupPage, BacktestDetailPage, HomePage } from './components';

// ReactDOM.createRoot(document.getElementById('root')!).render(
//   <React.StrictMode>
//     <ThemeProvider>
//       <Router>
//         <Routes>
//           <Route element={<HomePage />} path="/" />
//           <Route element={<BacktestSetupPage />} path="/backtest-setup" />
//           <Route element={<BacktestDetailPage />} path="/backtest-detail" />
//           <Route element={<HomePage />} path="*" />
//         </Routes>
//       </Router>
//     </ThemeProvider>
//   </React.StrictMode>
// );
