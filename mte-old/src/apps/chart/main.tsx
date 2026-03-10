import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import "@/styles/globals.css";
import { HuiProvider } from '@/components';

import { ChartApp } from './chart.app';

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <HuiProvider>
        <ChartApp />
      </HuiProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
