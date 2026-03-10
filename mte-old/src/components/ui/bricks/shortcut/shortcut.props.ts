import React from 'react';

export interface ShortcutProps {
  label: string;
  icon: React.ReactNode;
  isDisabled?: boolean;
  onClick: () => void;
}
