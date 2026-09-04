'use client';

import { useState, type FormEvent, type MouseEvent } from 'react';

import { PrimaryButton } from '@/components/PrimaryButton';
import { useProjectDashboardStore } from '@/features/projects/projectDashboardStore';

export function CreateProjectOverlay() {
  const isCreateOverlayOpen = useProjectDashboardStore((state) => state.isCreateOverlayOpen);
  const closeCreateOverlay = useProjectDashboardStore((state) => state.closeCreateOverlay);
  const [projectName, setProjectName] = useState('');

  if (!isCreateOverlayOpen) {
    return null;
  }

  const isNameEmpty = projectName.trim().length === 0;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  function handleBackdropMouseDown(event: MouseEvent<HTMLDivElement>) {
    event.preventDefault();
    event.stopPropagation();
  }

  function handlePanelMouseDown(event: MouseEvent<HTMLDivElement>) {
    event.stopPropagation();
  }

  return (
    <div
      aria-modal="true"
      className="create-overlay"
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
              id="project-name"
              onChange={(event) => {
                setProjectName(event.target.value);
              }}
              type="text"
              value={projectName}
            />
          </label>
          <div className="create-overlay__actions">
            <PrimaryButton disabled={isNameEmpty} type="submit">
              Create
            </PrimaryButton>
            <button className="secondary-button" onClick={closeCreateOverlay} type="button">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
