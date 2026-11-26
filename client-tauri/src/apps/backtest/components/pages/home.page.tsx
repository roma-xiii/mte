import { BaseLayout, ButtonIconPlusBrick, HeaderLayout } from '@/components';
import { useNavigate } from 'react-router-dom';
import { BacktestListFeature, ConnectionStatusFeature } from '../features';

export const HomePage = () => {
  const navigate = useNavigate();
  return (
    <BaseLayout
      header={
        <HeaderLayout title="Backtests">
          <ButtonIconPlusBrick onClick={() => navigate('/backtest-setup')} />
        </HeaderLayout>
      }
    >
      <BacktestListFeature />
      <ConnectionStatusFeature />
    </BaseLayout>
  );
};
