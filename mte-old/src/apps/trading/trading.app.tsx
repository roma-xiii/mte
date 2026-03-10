import { Input } from '@heroui/input';
import React from 'react';


export const TradingApp = () => {
  const [formValue, formValueSet] = React.useState({
    priceEntry: 0.0,
    priceStopLoss: 0.0,
    deposit: 1000.00,
    riskPercentage: 1.00,
  });

  const changeFormValue = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.name === 'deposit' || e.target.name === 'riskPercentage' || 
                 e.target.name === 'priceEntry' || e.target.name === 'priceStopLoss'
      ? parseFloat(e.target.value) || 0
      : e.target.value;
      
    formValueSet((prev) => ({ ...prev, [e.target.name]: value }));
  }

  const qty = React.useMemo(() => {
    const riskHeight = formValue.priceEntry - formValue.priceStopLoss;
    const moneyRisk = (formValue.deposit / 100) * formValue.riskPercentage;
    return (moneyRisk / riskHeight).toFixed(2);
  }, [
    formValue,
  ]);

  return (
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
        }}
      >
        <div className="flex w-full flex-wrap md:flex-nowrap gap-4">
          <Input
            label="Deposit"
            onChange={changeFormValue}
            value={formValue.deposit.toString()}
            name="deposit"
            placeholder="Deposit"
            type="number"
            step="0.01"
          />
        </div>
        <div className="flex w-full flex-wrap md:flex-nowrap gap-4">
          <Input
            label="Risk percentage"
            onChange={changeFormValue}
            value={formValue.riskPercentage.toString()}
            name="riskPercentage"
            placeholder="Risk percentage"
            type="number"
            step="0.01"
          />
        </div>
        <br />
        <div className="flex w-full flex-wrap md:flex-nowrap gap-4">
          <Input
            label="Price entry"
            onChange={changeFormValue}
            value={formValue.priceEntry.toString()}
            name="priceEntry"
            placeholder="Price entry"
            type="number"
          />
        </div>
        <div className="flex w-full flex-wrap md:flex-nowrap gap-4">
          <Input
            label="StopLoss"
            onChange={changeFormValue}
            value={formValue.priceStopLoss.toString()}
            name="priceStopLoss"
            placeholder="StopLoss"
            type="number"
          />
        </div>

        <h4>Size: {qty}</h4>
      </form>
  );
}
