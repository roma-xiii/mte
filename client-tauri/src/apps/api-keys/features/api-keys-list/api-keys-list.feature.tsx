import { MainContextProvider } from './contexts';
import { MainComponent } from './components';

export const ApiKeysListFeature = () => {
  return (
    <MainContextProvider>
      <MainComponent />
    </MainContextProvider>
  );
};
