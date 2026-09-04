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
