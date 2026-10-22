import { RoleGuard } from '@/auth/RoleGuard';
import { KullanicilarEkrani } from '@/features/admin/KullanicilarEkrani';

export default function Kullanicilar() {
  return (
    <RoleGuard allow={['admin']}>
      <KullanicilarEkrani />
    </RoleGuard>
  );
}
