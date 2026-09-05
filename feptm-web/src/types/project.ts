export interface ProjectListItem {
  name: string;
  drive_folder_id: string;
}

export interface ProjectListResponse {
  projects: ProjectListItem[];
}

export interface ProjectMeta {
  created: string;
  modified: string;
  drive_folder_id?: string | null;
  drive_folder_url?: string | null;
  project_info_spreadsheet_id?: string | null;
  project_info_spreadsheet_url?: string | null;
  report_spreadsheet_id?: string | null;
  report_spreadsheet_url?: string | null;
  calculations_spreadsheet_id?: string | null;
  calculations_spreadsheet_url?: string | null;
}

export interface CreateProjectRequest {
  project_name: string;
}

export interface ProjectCardTable {
  label: string;
  spreadsheet_id: string;
  url: string;
}

export interface ProjectCardTimesheet {
  name: string;
  spreadsheet_id: string;
  url: string;
}

export interface ProjectCardTables {
  project_info: ProjectCardTable;
  general_expenses: ProjectCardTable;
  payment_distribution: ProjectCardTable;
}

export interface ProjectCardResponse {
  name: string;
  drive_folder_id: string;
  project_id: string;
  tables: ProjectCardTables;
  timesheets: ProjectCardTimesheet[];
}

export interface ProjectSyncRequest {
  project_id: string;
}

export interface ProjectSyncResponse {
  created: string;
  project_id: string;
  specialists_found: number;
  specialists_created: number;
}

export interface ProjectSyncRatesRequest {
  project_id: string;
}

export interface ProjectSyncRatesResponse {
  created: string;
  project_id: string;
  specialists_updated: number;
}

export interface ClosePeriodRequest {
  project_id: string;
  period_name: string;
}

export interface ClosePeriodResponse {
  created: string;
  project_id: string;
  period_name: string;
  entries_updated: number;
  specialists_processed: number;
  report_archived: boolean;
  calculations_archived: boolean;
}
