import { RoleGuard } from '@/auth/RoleGuard';
import { YeniHastaEkrani } from '@/features/yeni-hasta/YeniHastaEkrani';

export default function Yeni() {
  return (
    <RoleGuard allow={['doktor']}>
      <YeniHastaEkrani />
    </RoleGuard>
  );
}
