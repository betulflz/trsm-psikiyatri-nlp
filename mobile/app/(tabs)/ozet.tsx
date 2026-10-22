import { RoleGuard } from '@/auth/RoleGuard';
import { OzetEkrani } from '@/features/ozet/OzetEkrani';

export default function Ozet() {
  return (
    <RoleGuard allow={['doktor', 'hemsire']}>
      <OzetEkrani />
    </RoleGuard>
  );
}
