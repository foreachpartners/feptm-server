'use client';

import { useQuery } from '@tanstack/react-query';

import { fetchProjectList } from '@/lib/api/projects';

export function useProjectList() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: fetchProjectList,
    retry: 0,
  });
}
