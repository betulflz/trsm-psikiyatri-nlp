import { useLocalSearchParams } from 'expo-router';
import { RoleGuard } from '@/auth/RoleGuard';
import { DosyaDetayEkrani } from '@/features/dosya-detay/DosyaDetayEkrani';

export default function Dosya() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <RoleGuard allow={['doktor', 'hemsire']}>
      <DosyaDetayEkrani id={Number(id)} />
    </RoleGuard>
  );
}
