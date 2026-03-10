import { BackIcon } from '@/components/icons';
import { ActionIcon } from '@mantine/core';
import { ButtonIconBackProps } from './button-icon-back.props';
import { useNavigate } from 'react-router-dom';

export const ButtonIconBackBrick = ({ onClick }: ButtonIconBackProps) => {
  const navigate = useNavigate();

  return (
    <ActionIcon
      variant="default"
      size={42}
      onClick={onClick === undefined ? () => navigate(-1) : () => onClick()}
    >
      <BackIcon />
    </ActionIcon>
  );
};
