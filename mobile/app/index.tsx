import { Redirect } from 'expo-router';
import { useAuth } from '@/auth/AuthProvider';
import { homeTab } from '@/lib/roleTabs';

export default function Index() {
  const { user } = useAuth();
  if (!user) return <Redirect href="/giris" />;
  return <Redirect href={`/(tabs)/${homeTab(user.rol)}`} />;
}
