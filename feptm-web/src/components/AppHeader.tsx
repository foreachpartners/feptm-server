import type { ReactElement } from 'react';

import { ThemeToggle } from '@/components/ThemeToggle';

interface AppHeaderProps {
  inert?: boolean;
}

export function AppHeader({ inert }: AppHeaderProps): ReactElement {
  return (
    <header className="app-header" inert={inert || undefined}>
      <a
        className="app-header__brand"
        href="https://foreachpartners.com/"
        rel="noopener noreferrer"
        target="_blank"
      >
        <img
          src="/foreach-partners-logo.png"
          alt=""
          width={32}
          height={32}
          className="app-header__logo"
        />
        <span className="app-header__wordmark">ForEach Partners</span>
      </a>
      <ThemeToggle />
    </header>
  );
}
