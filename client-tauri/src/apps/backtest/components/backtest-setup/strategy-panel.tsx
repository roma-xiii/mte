import { useState, useEffect } from 'react';
import { Select, NumberInput, TextInput, Switch, Stack, Group, Button, Text } from '@mantine/core';
import type { StrategySchema, StrategyParam } from '../../types';

interface StrategyPanelProps {
  strategies: StrategySchema[];
  onStart: (_config: Record<string, unknown>) => void;
  loading: boolean;
  disabled: boolean;
  onBack: () => void;
}

function ParamInput({
  param,
  value,
  onChange,
}: {
  param: StrategyParam;
  value: unknown;
  onChange: (_v: unknown) => void;
}) {
  switch (param.type) {
    case 'int':
      return (
        <NumberInput
          label={param.label}
          value={value as number}
          onChange={(v) => onChange(typeof v === 'string' ? parseInt(v, 10) : v)}
          min={param.min}
          max={param.max}
        />
      );
    case 'float':
      return (
        <NumberInput
          label={param.label}
          value={value as number}
          onChange={(v) => onChange(typeof v === 'string' ? parseFloat(v) : v)}
          min={param.min}
          max={param.max}
          decimalScale={2}
        />
      );
    case 'select':
      return (
        <Select
          label={param.label}
          data={param.options || []}
          value={value as string}
          onChange={(v) => onChange(v)}
        />
      );
    case 'bool':
      return (
        <Switch
          label={param.label}
          checked={value as boolean}
          onChange={(e) => onChange(e.currentTarget.checked)}
        />
      );
    case 'string':
      return (
        <TextInput
          label={param.label}
          value={value as string}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
    default:
      return (
        <TextInput
          label={param.label}
          value={String(value)}
          onChange={(e) => onChange(e.currentTarget.value)}
        />
      );
  }
}

export function StrategyPanel({ strategies, onStart, loading, disabled, onBack }: StrategyPanelProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [startBalance, setStartBalance] = useState(1_000_000);
  const [accountType, setAccountType] = useState('margin');
  const [leverage, setLeverage] = useState(1);

  const currentSchema = strategies.find((s) => s.name === selectedStrategy);

  useEffect(() => {
    if (
      strategies.length > 0 &&
      !strategies.some((strategy) => strategy.name === selectedStrategy)
    ) {
      setSelectedStrategy(strategies[0].name);
    }
  }, [strategies, selectedStrategy]);

  useEffect(() => {
    if (currentSchema) {
      const defaults: Record<string, unknown> = {};
      for (const [key, param] of Object.entries(currentSchema.params)) {
        defaults[key] = param.default;
      }
      setParams(defaults);
    }
  }, [currentSchema]);

  const handleStart = () => {
    if (disabled || !currentSchema) return;
    onStart({
      strategy_name: selectedStrategy,
      strategy_params: params,
      starting_balance: startBalance,
      account_type: accountType,
      leverage,
    });
  };

  const strategyOptions = strategies.map((s) => ({ value: s.name, label: s.label }));

  return (
    <Stack gap="sm">
      <Select
        label="Strategy"
        data={strategyOptions}
        value={selectedStrategy}
        onChange={setSelectedStrategy}
        searchable
      />

      {currentSchema && (
        <Stack gap="xs">
          <Text size="sm" fw={500}>
            Parameters
          </Text>
          {Object.entries(currentSchema.params).map(([key, param]) => (
            <ParamInput
              key={key}
              param={param}
              value={params[key]}
              onChange={(v) => setParams((prev) => ({ ...prev, [key]: v }))}
            />
          ))}
        </Stack>
      )}

      <Text size="sm" fw={500}>
        Account
      </Text>
      <NumberInput
        label="Starting Balance"
        value={startBalance}
        onChange={(v) => setStartBalance(typeof v === 'string' ? parseFloat(v) : v)}
        min={0}
        decimalScale={0}
      />
      <Select
        label="Account type"
        data={['margin', 'cash']}
        value={accountType}
        onChange={(v) => setAccountType(v || 'margin')}
      />
      <NumberInput
        label="Leverage"
        value={leverage}
        onChange={(v) => setLeverage(typeof v === 'string' ? parseInt(v, 10) : v)}
        min={1}
        max={100}
      />

      <Group grow mt="md">
        <Button variant="default" size="lg" onClick={onBack}>
          Back
        </Button>
        <Button
          size="lg"
          onClick={handleStart}
          loading={loading}
          disabled={disabled || !currentSchema}
        >
          Start Backtest
        </Button>
      </Group>
    </Stack>
  );
}
