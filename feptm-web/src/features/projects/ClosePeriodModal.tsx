'use client';

import { useState, type FormEvent, type KeyboardEvent, type MouseEvent, type ReactElement } from 'react';

import { PrimaryButton } from '@/components/PrimaryButton';
import {
  PROJECT_CLOSE_PERIOD_ERROR,
  PROJECT_PERIOD_ALREADY_CLOSED,
} from '@/lib/api/projects';
import { ApiClientError } from '@/lib/api/errors';

interface ClosePeriodModalProps {
  isBusy: boolean;
  isPending: boolean;
  isSuccess: boolean;
  error: Error | null;
  periodNameFromResponse: string | null;
  onCancel: () => void;
  onConfirm: (periodName: string) => void;
}

function closePeriodErrorText(error: Error | null): string {
  if (error instanceof ApiClientError && error.status === 409) {
    return PROJECT_PERIOD_ALREADY_CLOSED;
  }

  return PROJECT_CLOSE_PERIOD_ERROR;
}

export function ClosePeriodModal({
  isBusy,
  isPending,
  isSuccess,
  error,
  periodNameFromResponse,
  onCancel,
  onConfirm,
}: ClosePeriodModalProps): ReactElement {
  const [periodName, setPeriodName] = useState('');
  const isNameEmpty = periodName.trim().length === 0;
  const isConfirmDisabled = isNameEmpty || isPending || isSuccess;
  const isCancelDisabled = isPending;

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const trimmedName = periodName.trim();
    if (trimmedName.length === 0 || isPending || isSuccess) {
      return;
    }

    onConfirm(trimmedName);
  }

  function handleBackdropMouseDown(event: MouseEvent<HTMLDivElement>): void {
    event.preventDefault();
    event.stopPropagation();
  }

  function handlePanelMouseDown(event: MouseEvent<HTMLDivElement>): void {
    event.stopPropagation();
  }

  function handleOverlayKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === 'Escape' && isBusy) {
      event.preventDefault();
      event.stopPropagation();
    }
  }

  function handleCancel(): void {
    if (isPending) {
      return;
    }

    onCancel();
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
        <h2 className="create-overlay__title">Close period</h2>
        <form className="create-overlay__form" onSubmit={handleSubmit}>
          <label className="create-overlay__label" htmlFor="period-name">
            Period name
            <input
              className="create-overlay__input"
              disabled={isPending || isSuccess}
              id="period-name"
              onChange={(event) => {
                setPeriodName(event.target.value);
              }}
              type="text"
              value={periodName}
            />
          </label>
          <p className="create-overlay__warning">
            Important! All unclosed hours, rates, and dates will be fixed. After that they can be
            changed only by hand.
          </p>
          {isPending ? (
            <p aria-live="polite" className="create-overlay__status" role="status">
              Closing period...
            </p>
          ) : null}
          {isSuccess && periodNameFromResponse ? (
            <p aria-live="polite" className="create-overlay__status" role="status">
              Period closed: {periodNameFromResponse}.
            </p>
          ) : null}
          {error && !isPending && !isSuccess ? (
            <p aria-live="polite" className="create-overlay__error" role="alert">
              {closePeriodErrorText(error)}
            </p>
          ) : null}
          <div className="create-overlay__actions">
            <PrimaryButton disabled={isConfirmDisabled} type="submit">
              Confirm
            </PrimaryButton>
            <button
              className="secondary-button"
              disabled={isCancelDisabled}
              onClick={handleCancel}
              type="button"
            >
              Close
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
