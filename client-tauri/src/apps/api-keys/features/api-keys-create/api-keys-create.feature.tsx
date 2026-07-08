import { MainContextProvider } from './contexts';
import { MainComponent } from './components';

export const ApiKeysCreateFeature = () => {
  return (
    <MainContextProvider>
      <MainComponent />
    </MainContextProvider>
  );
};
