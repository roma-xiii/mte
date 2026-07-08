import { PlusIcon } from '@/components/icons';
import { ActionIcon } from '@mantine/core';
import { ButtonIconPlusProps } from './button-icon-plus.props';

export const ButtonIconPlusBrick = ({ onClick }: ButtonIconPlusProps) => {
  return (
    <ActionIcon variant="default" size={42} onClick={onClick} radius="md">
      <PlusIcon />
    </ActionIcon>
  );
};
