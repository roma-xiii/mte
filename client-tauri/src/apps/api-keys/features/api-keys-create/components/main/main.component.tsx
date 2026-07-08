import { ButtonCancelBrick, ButtonSaveBrick } from '@/components';
import { Box, Card, Divider, Flex, Group, Input } from '@mantine/core';
import { IconChevronDown } from '@tabler/icons-react';

export const MainComponent = () => {
  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Flex justify="center">
        <Box miw={420}>
          <Box mb="md">
            <Input.Wrapper label="Source">
              <Input
                component="select"
                rightSection={<IconChevronDown size={14} stroke={1.5} />}
                pointer
              >
                <option value="bybit-spot">Bybit Spot</option>
                <option value="bybit-futures">Bybit Futures</option>
                <option value="binance-spot">Binance Spot</option>
                <option value="binance-futures">Binance Futures</option>
              </Input>
            </Input.Wrapper>
          </Box>

          <Box mb="md">
            <Input.Wrapper label="ApiKey">
              <Input size="md" value="" placeholder="Enter key" />
            </Input.Wrapper>
          </Box>

          <Input.Wrapper label="ApiKey Secret">
            <Input size="md" value="" placeholder="Enter secret" />
          </Input.Wrapper>

          <Divider my="md" />

          <Group gap="xs">
            <ButtonSaveBrick />
            <ButtonCancelBrick />
          </Group>
        </Box>
      </Flex>
    </Card>
  );
};
