import path from 'node:path';
import type { NextConfig } from 'next';

const DEFAULT_API_ORIGIN = 'http://localhost:8000';

function resolveApiOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }

  console.warn(
    `[feptm-web] NEXT_PUBLIC_API_URL is not set; using ${DEFAULT_API_ORIGIN}. Copy env.example to .env.local to override.`,
  );
  return DEFAULT_API_ORIGIN;
}

const apiOrigin = resolveApiOrigin();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.resolve(process.cwd()),
  skipTrailingSlashRedirect: true,

  async rewrites() {
    return [
      {
        source: '/api/projects',
        destination: `${apiOrigin}/api/projects/`,
      },
      {
        source: '/api/projects/',
        destination: `${apiOrigin}/api/projects/`,
      },
      {
        source: '/api/:path*',
        destination: `${apiOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
