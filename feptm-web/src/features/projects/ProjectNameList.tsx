import Link from 'next/link';

import { projectCardHref } from '@/features/projects/projectCardHref';
import type { ProjectListItem } from '@/types/project';

interface ProjectNameListProps {
  projects: ProjectListItem[];
}

export function ProjectNameList({ projects }: ProjectNameListProps) {
  const sorted = [...projects].sort((left, right) =>
    left.name.localeCompare(right.name, undefined, { sensitivity: 'base' }),
  );

  return (
    <ul className="project-name-list">
      {sorted.map((project) => {
        const href = projectCardHref(project.drive_folder_id, project.name);

        return (
          <li className="project-name-list__item" key={project.drive_folder_id}>
            <Link
              className="project-name-list__link"
              href={href}
              rel="noopener noreferrer"
              target="_blank"
            >
              {project.name}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
