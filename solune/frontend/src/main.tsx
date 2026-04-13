/**
 * Application entry point.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import { ThemeProvider } from './components/ThemeProvider';
import { logger } from './lib/logger';

/* ── Global error telemetry ── */
window.onerror = (message, source, lineno, colno, error) => {
  logger.error('global:onerror', 'Unhandled window error', {
    colno,
    error,
    lineno,
    message: String(message),
    source,
  });
};

window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
  logger.error('global:unhandledrejection', 'Unhandled promise rejection', {
    reason: event.reason,
  });
});

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <StrictMode>
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <App />
      </ThemeProvider>
    </StrictMode>
  );
}
