import { Card, Table } from '@mantine/core';
import { useMainContext } from '../../contexts';

export const MainComponent = () => {
  const { apiKeyList } = useMainContext();

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Source</Table.Th>
            <Table.Th>Key</Table.Th>
            <Table.Th>Secret</Table.Th>
            <Table.Th>Created</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {apiKeyList.map((apiKey) => (
            <Table.Tr key={apiKey.name}>
              <Table.Td>{apiKey.name}</Table.Td>
              <Table.Td>{apiKey.source}</Table.Td>
              <Table.Td>{apiKey.key}</Table.Td>
              <Table.Td>{apiKey.secret}</Table.Td>
              <Table.Td>{apiKey.createdAt}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
};
