'use client';

import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { fetchProjectCard } from '@/lib/api/projects';
import type { ProjectCardResponse } from '@/types/project';

export function useProjectCard(driveFolderId: string): UseQueryResult<ProjectCardResponse, Error> {
  return useQuery({
    enabled: driveFolderId.length > 0,
    queryFn: () => fetchProjectCard(driveFolderId),
    queryKey: ['project-card', driveFolderId],
    retry: 0,
  });
}
