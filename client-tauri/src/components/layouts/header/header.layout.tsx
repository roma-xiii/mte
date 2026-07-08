import { Container, Flex, Title } from '@mantine/core';
import { HeaderProps } from './header.props';

export const HeaderLayout = ({ title, children }: HeaderProps) => {
  return (
    <Container fluid>
      <Flex mih={60} gap="md" justify="space-between" align="center" direction="row" wrap="wrap">
        <Title order={3}>{title}</Title>
        <Flex mih={60} gap="xs" justify="flex-end" align="center" direction="row" wrap="wrap">
          {children}
        </Flex>
      </Flex>
    </Container>
  );
};
