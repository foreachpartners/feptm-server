'use client';

import { useEffect, useState, type FormEvent, type KeyboardEvent, type MouseEvent, type ReactElement } from 'react';

import { PrimaryButton } from '@/components/PrimaryButton';
import { useCreateProject } from '@/features/projects/useCreateProject';
import { useProjectDashboardStore } from '@/features/projects/projectDashboardStore';
import { PROJECT_CREATE_ERROR } from '@/lib/api/projects';

export function CreateProjectOverlay(): ReactElement | null {
  const isCreateOverlayOpen = useProjectDashboardStore((state) => state.isCreateOverlayOpen);
  const closeCreateOverlay = useProjectDashboardStore((state) => state.closeCreateOverlay);
  const [projectName, setProjectName] = useState('');
  const createProject = useCreateProject();
  const resetCreate = createProject.reset;

  useEffect(() => {
    if (isCreateOverlayOpen) {
      setProjectName('');
      resetCreate();
    }
  }, [isCreateOverlayOpen, resetCreate]);

  if (!isCreateOverlayOpen) {
    return null;
  }

  const isNameEmpty = projectName.trim().length === 0;
  const isBusy = createProject.isPending;
  const isCreateDisabled = isNameEmpty || isBusy;

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const trimmedName = projectName.trim();
    if (trimmedName.length === 0 || createProject.isPending) {
      return;
    }

    const placeholderHref = new URL('/creating.html', window.location.origin).href;
    const cardTab = window.open(placeholderHref, '_blank');
    createProject.mutate({ cardTab, name: trimmedName });
  }

  function handleBackdropMouseDown(event: MouseEvent<HTMLDivElement>): void {
    event.preventDefault();
    event.stopPropagation();
  }

  function handlePanelMouseDown(event: MouseEvent<HTMLDivElement>): void {
    event.stopPropagation();
  }

  function handleCancel(): void {
    if (createProject.isPending) {
      return;
    }

    setProjectName('');
    createProject.reset();
    closeCreateOverlay();
  }

  function handleOverlayKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === 'Escape' && createProject.isPending) {
      event.preventDefault();
      event.stopPropagation();
    }
  }

  return (
    <div
      aria-modal="true"
      className="create-overlay"
      onKeyDown={handleOverlayKeyDown}
      onMouseDown={handleBackdropMouseDown}
      role="dialog"
    >
      <div className="create-overlay__panel" onMouseDown={handlePanelMouseDown}>
        <h2 className="create-overlay__title">Create project</h2>
        <form className="create-overlay__form" onSubmit={handleSubmit}>
          <label className="create-overlay__label" htmlFor="project-name">
            Project name
            <input
              className="create-overlay__input"
              disabled={isBusy}
              id="project-name"
              onChange={(event) => {
                setProjectName(event.target.value);
              }}
              type="text"
              value={projectName}
            />
          </label>
          {isBusy ? (
            <p aria-live="polite" className="create-overlay__status" role="status">
              Creating...
            </p>
          ) : null}
          {createProject.isError ? (
            <p aria-live="polite" className="create-overlay__error" role="alert">
              {PROJECT_CREATE_ERROR}
            </p>
          ) : null}
          <div className="create-overlay__actions">
            <PrimaryButton disabled={isCreateDisabled} type="submit">
              Create
            </PrimaryButton>
            <button
              className="secondary-button"
              disabled={isBusy}
              onClick={handleCancel}
              type="button"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
