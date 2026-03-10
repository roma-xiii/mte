import { BaseLayout, HeaderLayout } from '@/components';
import { ButtonIconBackBrick } from '@/components';

import { ApiKeysCreateFeature } from '../../features';

export const ApiKeyCreatePage = () => {
  return (
    <BaseLayout
      header={
        <HeaderLayout title="ApiKeys Create">
          <ButtonIconBackBrick />
        </HeaderLayout>
      }
    >
      <ApiKeysCreateFeature />
    </BaseLayout>
  );
};
