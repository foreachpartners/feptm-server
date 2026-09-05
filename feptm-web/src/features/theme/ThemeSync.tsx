'use client';

import { useEffect } from 'react';

import { useThemeStore } from '@/features/theme/themeStore';

export function ThemeSync(): null {
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return null;
}
