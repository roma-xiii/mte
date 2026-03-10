import { Button } from '@heroui/button';

import styles from './shortcut.module.scss';
import { ShortcutProps } from './shortcut.props';

export const ShortcutBrick = ({
  label,
  icon,
  isDisabled,
  onClick,
}: ShortcutProps) => {
  return (
    <Button
      className={styles['shortcut']}
      isDisabled={isDisabled}
      onPress={onClick}
    >
      <div className={styles['shortcut__label']}>{label}</div>
      <div className={styles['shortcut__icon']}>{icon}</div>
    </Button>
  );
};
