import { RoleGuard } from '@/auth/RoleGuard';
import { DosyalarEkrani } from '@/features/dosyalar/DosyalarEkrani';

export default function Dosyalar() {
  return (
    <RoleGuard allow={['doktor', 'hemsire']}>
      <DosyalarEkrani />
    </RoleGuard>
  );
}
