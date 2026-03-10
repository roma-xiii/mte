import type { NavigateOptions } from 'react-router-dom';

import { useHref, useNavigate } from 'react-router-dom';
import { HeroUIProvider } from '@heroui/react';

declare module '@react-types/shared' {
  interface RouterConfig {
    routerOptions: NavigateOptions;
  }
}

export function HuiProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();

  return (
    <HeroUIProvider navigate={navigate} useHref={useHref}>
      <main
        className="dark text-foreground bg-background"
        style={{ height: '100vh' }}
      >
        {children}
      </main>
    </HeroUIProvider>
  );
}
