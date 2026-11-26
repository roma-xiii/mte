import React from 'react';
import { Button, Stack, Stepper } from '@mantine/core';

export const BacktestSetupFeature = () => {
  const [activeStep, activeStepSet] = React.useState(0);
  return (
    <Stack gap="md">
      <Stepper active={activeStep} allowNextStepsSelect={false}>
        <Stepper.Step label="Data Source">
          <h1>DataSource</h1>
          {/* <DataSourcePanel
            value={dataConfig}
            onChange={setDataConfig}
            dataFiles={dataFiles}
            onOpenDataManager={onOpenDataManager}
            onNext={() => setActiveStep(1)}
          /> */}
          <Button fullWidth size="lg" onClick={() => activeStepSet(1)} mt="md">
            Next
          </Button>
        </Stepper.Step>
        <Stepper.Step label="Strategy">
          <h1>DataStrategy</h1>
          {/* <StrategyPanel
            strategies={strategies}
            onStart={handleStart}
            loading={loading}
            disabled={disabled}
            onBack={() => setActiveStep(0)}
          /> */}
          <Button fullWidth size="lg" onClick={() => activeStepSet(0)} mt="md">
            Next
          </Button>
        </Stepper.Step>
      </Stepper>
    </Stack>
  );
};
