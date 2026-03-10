import { ShortcutsProps } from './shortcuts.props';
import styles from './shortcuts.module.scss';

export const ShortcutsLayout = ({ children }: ShortcutsProps) => {
  return <div className={styles['shortcuts-layout']}>{children}</div>;
};
