import { RoleGuard } from '@/auth/RoleGuard';
import { SistemEkrani } from '@/features/admin/SistemEkrani';

export default function Sistem() {
  return (
    <RoleGuard allow={['admin']}>
      <SistemEkrani />
    </RoleGuard>
  );
}
