import type { ReactNode } from 'react';

interface PrimaryButtonProps {
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit';
}

export function PrimaryButton({
  children,
  disabled,
  onClick,
  type = 'button',
}: PrimaryButtonProps) {
  return (
    <button className="primary-button" disabled={disabled} onClick={onClick} type={type}>
      {children}
    </button>
  );
}
