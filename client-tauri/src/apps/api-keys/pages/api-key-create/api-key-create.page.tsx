import { BaseLayout, HeaderLayout } from '@/components';
import { ButtonIconBackBrick } from '@/components';

import { ApiKeysCreateFeature } from '../../features';

export const ApiKeyCreatePage = () => {
  return (
    <BaseLayout
      header={
        <HeaderLayout title="ApiKey Create">
          <ButtonIconBackBrick />
        </HeaderLayout>
      }
    >
      <ApiKeysCreateFeature />
    </BaseLayout>
  );
};
