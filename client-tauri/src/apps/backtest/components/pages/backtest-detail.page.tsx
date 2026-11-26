import { useNavigate } from 'react-router-dom';
import { ConnectionStatusFeature } from '../features';

export const BacktestDetailPage = () => {
  const navigate = useNavigate();

  return (
    <div>
      <h1>Backtest Detail</h1>
      <ConnectionStatusFeature />
      <button onClick={() => navigate('/')}>Home</button>
      <button onClick={() => navigate('/backtest-setup')}>Setup</button>
      <button onClick={() => navigate('/backtest-detail')}>Detail</button>
    </div>
  );
};
