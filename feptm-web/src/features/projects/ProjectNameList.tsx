import Link from 'next/link';

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
        const href = `/projects/${encodeURIComponent(project.drive_folder_id)}?name=${encodeURIComponent(project.name)}`;

        return (
          <li className="project-name-list__item" key={project.drive_folder_id}>
            <Link className="project-name-list__link" href={href}>
              {project.name}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
