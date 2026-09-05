'use client';

import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { useState, type ReactElement } from 'react';

import { AppHeader } from '@/components/AppHeader';
import { PrimaryButton } from '@/components/PrimaryButton';
import { ClosePeriodModal } from '@/features/projects/ClosePeriodModal';
import { ProjectCardTables } from '@/features/projects/ProjectCardTables';
import { useProjectCard } from '@/features/projects/useProjectCard';
import {
  useCloseProjectPeriod,
  useSyncProjectRates,
  useSyncProjectTeam,
} from '@/features/projects/useProjectCommands';
import {
  PROJECT_CARD_LOAD_ERROR,
  PROJECT_SYNC_RATES_ERROR,
  PROJECT_SYNC_TEAM_ERROR,
} from '@/lib/api/projects';

function readDriveFolderId(projectId: string | string[] | undefined): string {
  if (typeof projectId === 'string') {
    return projectId;
  }

  const firstId = projectId?.[0];
  return typeof firstId === 'string' ? firstId : '';
}

export function ProjectCard(): ReactElement {
  const params = useParams();
  const searchParams = useSearchParams();
  const driveFolderId = readDriveFolderId(params.projectId);
  const nameHint = searchParams.get('name') ?? '';

  const cardQuery = useProjectCard(driveFolderId);
  const teamMutation = useSyncProjectTeam();
  const ratesMutation = useSyncProjectRates();
  const closeMutation = useCloseProjectPeriod();
  const [isCloseOpen, setIsCloseOpen] = useState(false);

  const isCommandBusy =
    teamMutation.isPending || ratesMutation.isPending || closeMutation.isPending;
  const projectId = cardQuery.data?.project_id;
  const commandsDisabled = isCommandBusy || projectId === undefined;
  const displayName = cardQuery.data?.name ?? nameHint;

  function handleUpdateTeam(): void {
    if (projectId === undefined || isCommandBusy) {
      return;
    }

    ratesMutation.reset();
    closeMutation.reset();
    teamMutation.mutate({ driveFolderId, projectId });
  }

  function handleUpdateRates(): void {
    if (projectId === undefined || isCommandBusy) {
      return;
    }

    teamMutation.reset();
    closeMutation.reset();
    ratesMutation.mutate({ driveFolderId, projectId });
  }

  function handleOpenClosePeriod(): void {
    if (projectId === undefined || isCommandBusy) {
      return;
    }

    teamMutation.reset();
    ratesMutation.reset();
    closeMutation.reset();
    setIsCloseOpen(true);
  }

  function handleClosePeriodCancel(): void {
    setIsCloseOpen(false);
    closeMutation.reset();
  }

  function handleClosePeriodConfirm(periodName: string): void {
    if (projectId === undefined || closeMutation.isPending) {
      return;
    }

    closeMutation.mutate({ period_name: periodName, project_id: projectId });
  }

  let cardStatus: string | null = null;
  let cardStatusIsError = false;

  if (cardQuery.isPending) {
    cardStatus = 'Loading...';
  } else if (cardQuery.isError) {
    cardStatus = PROJECT_CARD_LOAD_ERROR;
    cardStatusIsError = true;
  } else if (teamMutation.isPending) {
    cardStatus = 'Updating team...';
  } else if (ratesMutation.isPending) {
    cardStatus = 'Updating rates...';
  } else if (teamMutation.isSuccess && teamMutation.data) {
    cardStatus = `Timesheets created: ${String(teamMutation.data.specialists_created)}.`;
  } else if (ratesMutation.isSuccess && ratesMutation.data) {
    cardStatus = `Rates updated: ${String(ratesMutation.data.specialists_updated)}.`;
  } else if (teamMutation.isError) {
    cardStatus = PROJECT_SYNC_TEAM_ERROR;
    cardStatusIsError = true;
  } else if (ratesMutation.isError) {
    cardStatus = PROJECT_SYNC_RATES_ERROR;
    cardStatusIsError = true;
  }

  return (
    <>
      <AppHeader inert={isCloseOpen || undefined} />
      <main className="project-card" inert={isCloseOpen || undefined}>
        {isCommandBusy ? (
          <button className="project-card__back" disabled type="button">
            Back to project list
          </button>
        ) : (
          <Link className="project-card__back" href="/">
            Back to project list
          </Link>
        )}
        <h1 className="project-card__heading">
          <span className="project-card__heading-label">Project</span>
          {displayName.length > 0 ? (
            <>
              {' '}
              <span className="project-card__heading-name">{displayName}</span>
            </>
          ) : null}
        </h1>
        <div className="project-card__commands">
          <PrimaryButton disabled={commandsDisabled} onClick={handleUpdateTeam}>
            Update team
          </PrimaryButton>
          <PrimaryButton disabled={commandsDisabled} onClick={handleUpdateRates}>
            Update rates
          </PrimaryButton>
          <PrimaryButton disabled={commandsDisabled} onClick={handleOpenClosePeriod}>
            Close period
          </PrimaryButton>
        </div>
        {cardStatus ? (
          <p
            aria-live="polite"
            className={cardStatusIsError ? 'project-card__error' : 'project-card__status'}
            role={cardStatusIsError ? 'alert' : 'status'}
          >
            {cardStatus}
          </p>
        ) : null}
        {cardQuery.data ? (
          <ProjectCardTables tables={cardQuery.data.tables} timesheets={cardQuery.data.timesheets} />
        ) : null}
      </main>
      <footer className="app-footer" inert={isCloseOpen || undefined}>
        <p className="app-footer__inner">© 2026 ForEach Partners</p>
      </footer>
      {isCloseOpen ? (
        <ClosePeriodModal
          error={closeMutation.error}
          isBusy={isCommandBusy}
          isPending={closeMutation.isPending}
          isSuccess={closeMutation.isSuccess}
          onCancel={handleClosePeriodCancel}
          onConfirm={handleClosePeriodConfirm}
          periodNameFromResponse={closeMutation.data?.period_name ?? null}
        />
      ) : null}
    </>
  );
}
