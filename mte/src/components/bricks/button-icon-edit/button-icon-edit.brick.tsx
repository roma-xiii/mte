import { EditIcon } from '@/components/icons';
import { ActionIcon } from '@mantine/core';
import { ButtonIconPlusProps } from './button-icon-edit.props';

export const ButtonIconEditBrick = ({ onClick }: ButtonIconPlusProps) => {
  return (
    <ActionIcon variant="default" size={42} onClick={onClick}>
      <EditIcon />
    </ActionIcon>
  );
};
