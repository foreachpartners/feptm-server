'use client';

import { AppHeader } from '@/components/AppHeader';
import { PrimaryButton } from '@/components/PrimaryButton';
import { CreateProjectOverlay } from '@/features/projects/CreateProjectOverlay';
import { ProjectNameList } from '@/features/projects/ProjectNameList';
import { useProjectDashboardStore } from '@/features/projects/projectDashboardStore';
import { PROJECT_LIST_LOAD_ERROR } from '@/lib/api/projects';
import { useProjectList } from '@/features/projects/useProjectList';

export function ProjectDashboard() {
  const { data, isError, isPending } = useProjectList();
  const openCreateOverlay = useProjectDashboardStore((state) => state.openCreateOverlay);

  return (
    <>
      <AppHeader />
      <main className="dashboard">
        <div className="dashboard__toolbar">
          <h1 className="dashboard__heading">FEP Projects Dashboard</h1>
          <PrimaryButton onClick={openCreateOverlay}>Create project</PrimaryButton>
        </div>
        {isPending ? <p className="dashboard__status">Loading...</p> : null}
        {isError ? <p className="dashboard__error">{PROJECT_LIST_LOAD_ERROR}</p> : null}
        {data && data.projects.length === 0 ? (
          <p className="dashboard__empty">no projects</p>
        ) : null}
        {data && data.projects.length > 0 ? <ProjectNameList projects={data.projects} /> : null}
      </main>
      <footer className="app-footer">
        <p className="app-footer__inner">© 2026 ForEach Partners</p>
      </footer>
      <CreateProjectOverlay />
    </>
  );
}
