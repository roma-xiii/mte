import { useNavigate } from 'react-router-dom';
import { Button } from '@mantine/core';
import { ButtonCancelBrickProps } from './button-cancel.props';

export const ButtonCancelBrick = ({ onClick }: ButtonCancelBrickProps) => {
  const navigate = useNavigate();

  return (
    <Button
      variant="outline"
      onClick={onClick === undefined ? () => navigate(-1) : () => onClick()}
    >
      Cancel
    </Button>
  );
};
