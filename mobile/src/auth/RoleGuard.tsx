import type { ReactNode } from 'react';
import { ApiError } from '@/api/errors';
import type { Rol } from '@/lib/roleTabs';
import { ErrorState, Screen } from '@/ui';
import { useAuth } from './AuthProvider';

export function RoleGuard({ allow, children }: { allow: Rol[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user || !allow.includes(user.rol)) {
    return (
      <Screen scroll={false}>
        <ErrorState error={new ApiError('yasak', 403, 'Bu alan rolünüze kapalı.')} />
      </Screen>
    );
  }
  return <>{children}</>;
}
