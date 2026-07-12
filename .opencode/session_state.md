# Session State

## Phase 3 — Frontend (TypeScript + React + Mantine + lightweight-charts v5)

### Components written (all compile clean)
| Component | File | Status |
|---|---|---|
| Types | `types.ts` | Done |
| Store hook | `hooks/useBacktestStore.ts` | Done |
| Chart | `components/chart/chart.tsx` | Done (v5 API: addSeries + createSeriesMarkers) |
| Data source panel | `components/backtest-setup/data-source-panel.tsx` | Done |
| Strategy panel | `components/backtest-setup/strategy-panel.tsx` | Done |
| Backtest setup | `components/backtest-setup/backtest-setup.tsx` | Done |
| Controls panel | `components/running-screen/controls-panel.tsx` | Done |
| Log/Trades panel | `components/running-screen/log-trades-panel.tsx` | Done |
| Running screen | `components/running-screen/running-screen.tsx` | Done |
| Data manager modal | `components/data-manager/data-manager-modal.tsx` | Done |
| Root app | `backtest.app.tsx` | Done |
| Entry point | `main.tsx` | Done |

### Verified
- `npx tsc --noEmit` passes with zero errors

### Notable decisions
- lightweight-charts v5: `chart.addSeries({ type: 'Candlestick' }, opts)` instead of old `addCandlestickSeries`
- Markers use `createSeriesMarkers(series).setMarkers(markers)` (v5 API change)
- Exits/indicators removed from Chart props for now (keep minimal)
- `snapshot` and `paused` event types added to BacktestEvent union
- Named export `BacktestApp` (not default) to match main.tsx import

### Next up
- Phase 4: Wire frontend ↔ Tauri ↔ Python end-to-end. Start Python WebSocket server, launch Tauri app, connect, run a backtest.
- Phase 5-7: Session persistence, polish, edge cases.
