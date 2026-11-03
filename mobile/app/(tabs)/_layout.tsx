import { Tabs } from 'expo-router';
import { useAuth } from '@/auth/AuthProvider';
import { ALL_TABS, tabsForRole } from '@/lib/roleTabs';
import { PillTabBar } from '@/ui';

export default function TabsLayout() {
  const { user } = useAuth();
  if (!user) return null;
  const visible = tabsForRole(user.rol);
  return (
    <Tabs
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <PillTabBar {...props} visible={visible} />}
    >
      {ALL_TABS.map((name) => (
        <Tabs.Screen key={name} name={name} options={{ href: visible.includes(name) ? undefined : null }} />
      ))}
    </Tabs>
  );
}
