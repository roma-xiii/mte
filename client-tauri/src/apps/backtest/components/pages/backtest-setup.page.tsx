import { useNavigate } from 'react-router-dom';
import { BaseLayout, ButtonIconPlusBrick, HeaderLayout } from '@/components';
import { BacktestSetupFeature, ConnectionStatusFeature } from '../features';

export const BacktestSetupPage = () => {
  const navigate = useNavigate();

  return (
    <BaseLayout
      header={
        <HeaderLayout title="Backtest Setup">
          <ButtonIconPlusBrick onClick={() => console.log('download')} />
        </HeaderLayout>
      }
    >
      <BacktestSetupFeature />
      <ConnectionStatusFeature />
      <button onClick={() => navigate('/')}>Home</button>
      <button onClick={() => navigate('/backtest-setup')}>Setup</button>
      <button onClick={() => navigate('/backtest-detail')}>Detail</button>
    </BaseLayout>
  );
};
