import type { ProjectListResponse } from '@/types/project';

export const PROJECT_LIST_LOAD_ERROR =
  'Failed to load the project list. Refresh the page or try again later.';

// @req FR-PROJECT-001
export async function fetchProjectList(): Promise<ProjectListResponse> {
  let response: Response;
  try {
    response = await fetch('/api/projects/');
  } catch {
    throw new Error(PROJECT_LIST_LOAD_ERROR);
  }

  if (!response.ok) {
    throw new Error(PROJECT_LIST_LOAD_ERROR);
  }

  const data: unknown = await response.json();
  if (!isProjectListResponse(data)) {
    throw new Error(PROJECT_LIST_LOAD_ERROR);
  }

  return data;
}

function isProjectListResponse(value: unknown): value is ProjectListResponse {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  if (!('projects' in value) || !Array.isArray(value.projects)) {
    return false;
  }

  return value.projects.every(isProjectListItem);
}

function isProjectListItem(value: unknown): boolean {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  if (!('name' in value) || !('drive_folder_id' in value)) {
    return false;
  }

  return typeof value.name === 'string' && typeof value.drive_folder_id === 'string';
}
