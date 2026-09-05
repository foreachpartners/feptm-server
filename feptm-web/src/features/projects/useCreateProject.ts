'use client';

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';

import { projectCardHref } from '@/features/projects/projectCardHref';
import { useProjectDashboardStore } from '@/features/projects/projectDashboardStore';
import { createProject } from '@/lib/api/projects';
import type { ProjectMeta } from '@/types/project';

export interface CreateProjectVariables {
  cardTab: Window | null;
  name: string;
}

export function useCreateProject(): UseMutationResult<
  ProjectMeta,
  Error,
  CreateProjectVariables,
  unknown
> {
  const queryClient = useQueryClient();
  const closeCreateOverlay = useProjectDashboardStore((state) => state.closeCreateOverlay);

  return useMutation({
    mutationFn: async (variables: CreateProjectVariables): Promise<ProjectMeta> => {
      const data = await createProject({ project_name: variables.name });
      if (!data.drive_folder_id) {
        throw new Error('missing drive_folder_id');
      }

      return data;
    },
    onError: (_error: Error, variables: CreateProjectVariables): void => {
      variables.cardTab?.close();
    },
    onSuccess: (data: ProjectMeta, variables: CreateProjectVariables): void => {
      const folderId = data.drive_folder_id;
      if (!folderId) {
        variables.cardTab?.close();
        return;
      }

      const href = new URL(projectCardHref(folderId, variables.name), window.location.origin).href;
      const cardTab = variables.cardTab;

      if (cardTab) {
        try {
          cardTab.location.replace(href);
          cardTab.opener = null;
        } catch {
          cardTab.close();
          window.open(href, '_blank', 'noopener,noreferrer');
        }
        closeCreateOverlay();
        void queryClient.invalidateQueries({ queryKey: ['projects'] });
        return;
      }

      window.open(href, '_blank', 'noopener,noreferrer');
      closeCreateOverlay();
      void queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
