import type { ReactElement } from 'react';

import type { ProjectCardTables as ProjectCardTablesModel, ProjectCardTimesheet } from '@/types/project';

interface ProjectCardTablesProps {
  tables: ProjectCardTablesModel;
  timesheets: readonly ProjectCardTimesheet[];
}

interface TableLink {
  key: string;
  label: string;
  url: string;
}

function collectTableLinks(
  tables: ProjectCardTablesModel,
  timesheets: readonly ProjectCardTimesheet[],
): TableLink[] {
  const projectSheets: TableLink[] = [
    {
      key: tables.project_info.spreadsheet_id,
      label: tables.project_info.label,
      url: tables.project_info.url,
    },
    {
      key: tables.general_expenses.spreadsheet_id,
      label: tables.general_expenses.label,
      url: tables.general_expenses.url,
    },
    {
      key: tables.payment_distribution.spreadsheet_id,
      label: tables.payment_distribution.label,
      url: tables.payment_distribution.url,
    },
  ];

  const timesheetLinks: TableLink[] = timesheets.map((timesheet) => ({
    key: timesheet.spreadsheet_id,
    label: timesheet.name,
    url: timesheet.url,
  }));

  return [...projectSheets, ...timesheetLinks].filter((link) => link.url.length > 0);
}

export function ProjectCardTables({ tables, timesheets }: ProjectCardTablesProps): ReactElement {
  const links = collectTableLinks(tables, timesheets);

  return (
    <section className="project-card__tables">
      <h2 className="project-card__tables-heading">Tables</h2>
      <ul className="project-card__table-list">
        {links.map((link) => (
          <li className="project-card__table-item" key={link.key}>
            <a
              className="project-card__table-link"
              href={link.url}
              rel="noopener noreferrer"
              target="_blank"
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
