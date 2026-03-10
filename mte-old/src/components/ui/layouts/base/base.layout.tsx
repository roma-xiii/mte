import { BaseProps } from './base.props';
import styles from './base.module.scss';

export const BaseLayout = ({ children }: BaseProps) => {
  return <div className={styles['base-layout']}>{children}</div>;
};
