'use client';

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';

import { closeProjectPeriod, syncProjectRates, syncProjectTeam } from '@/lib/api/projects';
import type {
  ClosePeriodRequest,
  ClosePeriodResponse,
  ProjectSyncRatesResponse,
  ProjectSyncResponse,
} from '@/types/project';

interface SyncCommandInput {
  driveFolderId: string;
  projectId: string;
}

export function useSyncProjectTeam(): UseMutationResult<
  ProjectSyncResponse,
  Error,
  SyncCommandInput,
  unknown
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: SyncCommandInput): Promise<ProjectSyncResponse> =>
      syncProjectTeam({ project_id: input.projectId }),
    onSuccess: (_data: ProjectSyncResponse, input: SyncCommandInput): void => {
      void queryClient.invalidateQueries({ queryKey: ['project-card', input.driveFolderId] });
    },
  });
}

export function useSyncProjectRates(): UseMutationResult<
  ProjectSyncRatesResponse,
  Error,
  SyncCommandInput,
  unknown
> {
  return useMutation({
    mutationFn: (input: SyncCommandInput): Promise<ProjectSyncRatesResponse> =>
      syncProjectRates({ project_id: input.projectId }),
  });
}

export function useCloseProjectPeriod(): UseMutationResult<
  ClosePeriodResponse,
  Error,
  ClosePeriodRequest,
  unknown
> {
  return useMutation({
    mutationFn: (request: ClosePeriodRequest): Promise<ClosePeriodResponse> =>
      closeProjectPeriod(request),
  });
}
