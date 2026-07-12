import { Modal, Table, Text, Button, Group, Stack, ActionIcon, Tooltip } from '@mantine/core';
import { IconTrash } from '@tabler/icons-react';
import type { DataFileInfo } from '../../types';

interface DataManagerModalProps {
  opened: boolean;
  onClose: () => void;
  dataFiles: DataFileInfo[];
  onDelete: (filename: string) => void;
  onRefresh: () => void;
}

export function DataManagerModal({
  opened,
  onClose,
  dataFiles,
  onDelete,
  onRefresh,
}: DataManagerModalProps) {
  return (
    <Modal opened={opened} onClose={onClose} title="Data Manager" size="lg">
      <Stack>
        <Group>
          <Text size="sm" c="dimmed">
            {dataFiles.length} file{dataFiles.length !== 1 ? 's' : ''} available
          </Text>
          <Button variant="light" size="xs" onClick={onRefresh}>
            Refresh
          </Button>
        </Group>
        {dataFiles.length === 0 ? (
          <Text c="dimmed" ta="center" py="xl">
            No data files found. Run a backtest to download data.
          </Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>File</Table.Th>
                <Table.Th>Symbol</Table.Th>
                <Table.Th>Timeframe</Table.Th>
                <Table.Th>Bars</Table.Th>
                <Table.Th>Date range</Table.Th>
                <Table.Th style={{ width: 60 }}></Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {dataFiles.map((f) => (
                <Table.Tr key={f.file}>
                  <Table.Td>
                    <Text size="sm">{f.file}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{f.instrument || '-'}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{f.timeframe || '-'}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{f.bars?.toLocaleString() || '-'}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {f.date_from && f.date_to ? `${f.date_from} → ${f.date_to}` : '-'}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Tooltip label="Delete file">
                      <ActionIcon color="red" variant="subtle" onClick={() => onDelete(f.file)}>
                        <IconTrash size={16} />
                      </ActionIcon>
                    </Tooltip>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
      </Stack>
    </Modal>
  );
}
