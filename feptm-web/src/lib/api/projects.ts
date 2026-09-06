import { ApiClientError } from '@/lib/api/errors';
import type {
  ClosePeriodRequest,
  ClosePeriodResponse,
  CreateProjectRequest,
  ProjectCardResponse,
  ProjectCardTable,
  ProjectCardTables,
  ProjectCardTimesheet,
  ProjectListResponse,
  ProjectMeta,
  ProjectSyncRatesResponse,
  ProjectSyncRequest,
  ProjectSyncResponse,
} from '@/types/project';

export const PROJECT_LIST_LOAD_ERROR =
  'Failed to load the project list. Refresh the page or try again later.';

export const PROJECT_CREATE_ERROR = 'Failed to create the project. Try again later.';

export const PROJECT_CARD_LOAD_ERROR =
  'Failed to load the project card. Refresh the page or try again later.';

export const PROJECT_SYNC_TEAM_ERROR = 'Failed to update the team. Try again later.';

export const PROJECT_SYNC_RATES_ERROR = 'Failed to update rates. Try again later.';

export const PROJECT_CLOSE_PERIOD_ERROR = 'Failed to close the period. Try again later.';

export const PROJECT_PERIOD_ALREADY_CLOSED = 'This period is already closed.';

const API_REQUEST_TIMEOUT_MS = 600_000;

const JSON_HEADERS: HeadersInit = {
  Accept: 'application/json',
};

const JSON_BODY_HEADERS: HeadersInit = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

async function readJson(response: Response, fallbackMessage: string): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new ApiClientError(fallbackMessage, 'invalid_json', response.status);
  }
}

async function requestJson(
  url: string,
  init: RequestInit,
  fallbackMessage: string,
): Promise<Response> {
  try {
    return await fetch(url, { ...init, signal: AbortSignal.timeout(API_REQUEST_TIMEOUT_MS) });
  } catch {
    throw new ApiClientError(fallbackMessage, 'network', null);
  }
}

// @req FR-PROJECT-001
export async function fetchProjectList(): Promise<ProjectListResponse> {
  const response = await requestJson('/api/projects/', { headers: JSON_HEADERS }, PROJECT_LIST_LOAD_ERROR);

  if (!response.ok) {
    throw new ApiClientError(PROJECT_LIST_LOAD_ERROR, 'api', response.status);
  }

  const data = await readJson(response, PROJECT_LIST_LOAD_ERROR);
  if (!isProjectListResponse(data)) {
    throw new ApiClientError(PROJECT_LIST_LOAD_ERROR, 'invalid_json', response.status);
  }

  return data;
}

// @req FR-CREATE-001
export async function createProject(request: CreateProjectRequest): Promise<ProjectMeta> {
  const response = await requestJson(
    '/api/projects/create',
    {
      method: 'POST',
      headers: JSON_BODY_HEADERS,
      body: JSON.stringify(request),
    },
    PROJECT_CREATE_ERROR,
  );

  if (!response.ok) {
    throw new ApiClientError(PROJECT_CREATE_ERROR, 'api', response.status);
  }

  const data = await readJson(response, PROJECT_CREATE_ERROR);
  if (!isProjectMeta(data) || !data.drive_folder_id) {
    throw new ApiClientError(PROJECT_CREATE_ERROR, 'invalid_json', response.status);
  }

  return data;
}

// @req FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001
export async function fetchProjectCard(driveFolderId: string): Promise<ProjectCardResponse> {
  const response = await requestJson(
    `/api/projects/${encodeURIComponent(driveFolderId)}/`,
    { headers: JSON_HEADERS },
    PROJECT_CARD_LOAD_ERROR,
  );

  if (!response.ok) {
    throw new ApiClientError(PROJECT_CARD_LOAD_ERROR, 'api', response.status);
  }

  const data = await readJson(response, PROJECT_CARD_LOAD_ERROR);
  if (!isProjectCardResponse(data)) {
    throw new ApiClientError(PROJECT_CARD_LOAD_ERROR, 'invalid_json', response.status);
  }

  return data;
}

// @req FR-SYNC-001
export async function syncProjectTeam(request: ProjectSyncRequest): Promise<ProjectSyncResponse> {
  const response = await requestJson(
    '/api/projects/sync',
    {
      method: 'POST',
      headers: JSON_BODY_HEADERS,
      body: JSON.stringify(request),
    },
    PROJECT_SYNC_TEAM_ERROR,
  );

  if (!response.ok) {
    throw new ApiClientError(PROJECT_SYNC_TEAM_ERROR, 'api', response.status);
  }

  const data = await readJson(response, PROJECT_SYNC_TEAM_ERROR);
  if (!isProjectSyncResponse(data)) {
    throw new ApiClientError(PROJECT_SYNC_TEAM_ERROR, 'invalid_json', response.status);
  }

  return data;
}

// @req FR-SYNC-RATES-001
export async function syncProjectRates(
  request: ProjectSyncRequest,
): Promise<ProjectSyncRatesResponse> {
  const response = await requestJson(
    '/api/projects/sync-rates',
    {
      method: 'POST',
      headers: JSON_BODY_HEADERS,
      body: JSON.stringify(request),
    },
    PROJECT_SYNC_RATES_ERROR,
  );

  if (!response.ok) {
    throw new ApiClientError(PROJECT_SYNC_RATES_ERROR, 'api', response.status);
  }

  const data = await readJson(response, PROJECT_SYNC_RATES_ERROR);
  if (!isProjectSyncRatesResponse(data)) {
    throw new ApiClientError(PROJECT_SYNC_RATES_ERROR, 'invalid_json', response.status);
  }

  return data;
}

// @req FR-PAYMENT-001
export async function closeProjectPeriod(request: ClosePeriodRequest): Promise<ClosePeriodResponse> {
  const response = await requestJson(
    '/api/periods',
    {
      method: 'PUT',
      headers: JSON_BODY_HEADERS,
      body: JSON.stringify(request),
    },
    PROJECT_CLOSE_PERIOD_ERROR,
  );

  if (response.status === 409) {
    throw new ApiClientError(PROJECT_PERIOD_ALREADY_CLOSED, 'api', 409);
  }

  if (!response.ok) {
    throw new ApiClientError(PROJECT_CLOSE_PERIOD_ERROR, 'api', response.status);
  }

  const data = await readJson(response, PROJECT_CLOSE_PERIOD_ERROR);
  if (!isClosePeriodResponse(data)) {
    throw new ApiClientError(PROJECT_CLOSE_PERIOD_ERROR, 'invalid_json', response.status);
  }

  return data;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isProjectListResponse(value: unknown): value is ProjectListResponse {
  if (!isRecord(value) || !Array.isArray(value.projects)) {
    return false;
  }

  return value.projects.every(isProjectListItem);
}

function isProjectListItem(value: unknown): boolean {
  if (!isRecord(value)) {
    return false;
  }

  return typeof value.name === 'string' && typeof value.drive_folder_id === 'string';
}

function isOptionalString(value: unknown): boolean {
  return value === undefined || value === null || typeof value === 'string';
}

function isProjectMeta(value: unknown): value is ProjectMeta {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.created === 'string' &&
    typeof value.modified === 'string' &&
    isOptionalString(value.drive_folder_id) &&
    isOptionalString(value.drive_folder_url) &&
    isOptionalString(value.project_info_spreadsheet_id) &&
    isOptionalString(value.project_info_spreadsheet_url) &&
    isOptionalString(value.report_spreadsheet_id) &&
    isOptionalString(value.report_spreadsheet_url) &&
    isOptionalString(value.calculations_spreadsheet_id) &&
    isOptionalString(value.calculations_spreadsheet_url)
  );
}

function isProjectCardTable(value: unknown): value is ProjectCardTable {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.label === 'string' &&
    typeof value.spreadsheet_id === 'string' &&
    typeof value.url === 'string'
  );
}

function isProjectCardTimesheet(value: unknown): value is ProjectCardTimesheet {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.name === 'string' &&
    typeof value.spreadsheet_id === 'string' &&
    typeof value.url === 'string'
  );
}

function isProjectCardTables(value: unknown): value is ProjectCardTables {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isProjectCardTable(value.project_info) &&
    isProjectCardTable(value.general_expenses) &&
    isProjectCardTable(value.payment_distribution)
  );
}

function isProjectCardResponse(value: unknown): value is ProjectCardResponse {
  if (!isRecord(value) || !Array.isArray(value.timesheets)) {
    return false;
  }

  return (
    typeof value.name === 'string' &&
    typeof value.drive_folder_id === 'string' &&
    typeof value.project_id === 'string' &&
    isProjectCardTables(value.tables) &&
    value.timesheets.every(isProjectCardTimesheet)
  );
}

function isProjectSyncResponse(value: unknown): value is ProjectSyncResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.created === 'string' &&
    typeof value.project_id === 'string' &&
    typeof value.specialists_found === 'number' &&
    typeof value.specialists_created === 'number'
  );
}

function isProjectSyncRatesResponse(value: unknown): value is ProjectSyncRatesResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.created === 'string' &&
    typeof value.project_id === 'string' &&
    typeof value.specialists_updated === 'number'
  );
}

function isClosePeriodResponse(value: unknown): value is ClosePeriodResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.created === 'string' &&
    typeof value.project_id === 'string' &&
    typeof value.period_name === 'string' &&
    typeof value.entries_updated === 'number' &&
    typeof value.specialists_processed === 'number' &&
    typeof value.report_archived === 'boolean' &&
    typeof value.calculations_archived === 'boolean'
  );
}
