import { Button } from '@mantine/core';
import { ButtonSaveBrickProps } from './button-save.props';

export const ButtonSaveBrick = ({ onClick }: ButtonSaveBrickProps) => {
  return <Button onClick={onClick}>Save</Button>;
};
