import React from 'react';

import { MainContextInterface, useMainHook } from './main.hook';

const MainContext = React.createContext<MainContextInterface | undefined>(undefined);

export const useMainContext = () => {
  const context = React.useContext(MainContext);

  if (context === undefined) {
    throw new Error('useMainContext must be used within MainProvider');
  }

  return context;
};

export const MainContextProvider = (props: React.HTMLAttributes<HTMLDivElement>) => {
  const hook = useMainHook();

  return <MainContext.Provider value={hook}>{props.children}</MainContext.Provider>;
};
