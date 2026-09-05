import type { ReactElement } from 'react';

import { ThemeToggle } from '@/components/ThemeToggle';

interface AppHeaderProps {
  inert?: boolean;
}

export function AppHeader({ inert }: AppHeaderProps): ReactElement {
  return (
    <header className="app-header" inert={inert || undefined}>
      <div className="app-header__brand">
        <img
          src="/foreach-partners-logo.png"
          alt=""
          width={32}
          height={32}
          className="app-header__logo"
        />
        <span className="app-header__wordmark">ForEach Partners</span>
      </div>
      <ThemeToggle />
    </header>
  );
}
