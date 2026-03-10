import { useNavigate } from 'react-router-dom';

import { BaseLayout, HeaderLayout } from '@/components';
import { ButtonIconPlusBrick } from '@/components';
import { ApiKeysListFeature } from '../../features';

export const ApiKeyListPage = () => {
  const navigate = useNavigate();

  return (
    <BaseLayout
      header={
        <HeaderLayout title="ApiKeys">
          <ButtonIconPlusBrick onClick={() => navigate('/create')} />
        </HeaderLayout>
      }
    >
      <ApiKeysListFeature />
    </BaseLayout>
  );
};
