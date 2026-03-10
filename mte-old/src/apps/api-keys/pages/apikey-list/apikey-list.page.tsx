import React from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Card, CardHeader, CardBody } from '@heroui/card';
import { Divider } from '@heroui/divider';
import { Button } from '@heroui/button';

import { BaseLayout, DeleteIcon, EditIcon, KeyIcon } from '@/components';

export const ApikeyListPage = () => {
  const apikeyListGet = async (): Promise<void> => {
    const result = await invoke('apikey_list');

    console.log(result);
  };

  const apikeyCreate = async (): Promise<void> => {
    const result = await invoke('apikey_create');

    console.log(result);
  };

  React.useEffect(() => {
    apikeyListGet();
  }, []);

  return (
    <BaseLayout>
      <Card>
        <CardHeader className="flex gap-3 justify-between">
          <KeyIcon />
          <div className="flex flex-col">
            <p className="text-md">My bybit</p>
            <p className="text-small text-default-500">BYBIT</p>
          </div>
          <div className="flex flex-col ml-auto">
            <div className="flex gap-1">
              <Button
                isIconOnly
                aria-label="Take a photo"
                color="default"
                variant="light"
                onPressEnd={apikeyCreate}
              >
                <DeleteIcon />
              </Button>
              <Button
                isIconOnly
                aria-label="Take a photo"
                color="default"
                variant="light"
              >
                <EditIcon />
              </Button>
            </div>
          </div>
        </CardHeader>
        <Divider />
        <CardBody>
          <p>
            Key: Make beautiful websites regardless of your design experience
          </p>
          <p>
            Secret: Make beautiful websites beautiful websites regardless of
            your design regardless of your
          </p>
        </CardBody>
      </Card>
    </BaseLayout>
  );
};
