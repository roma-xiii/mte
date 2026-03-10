import { CenteredProps } from './centered.props';
import styles from './centered.module.scss';

export const CenteredLayout = ({ children }: CenteredProps) => {
  return (
    <div className={styles['centered-layout']}>
      <div className={styles['centered-layout__wrap']}>{children}</div>
    </div>
  );
};
