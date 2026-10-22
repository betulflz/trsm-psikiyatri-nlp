import type { BottomTabBarProps } from 'expo-router/build/layouts/Tabs';
import { Folder, LayoutGrid, Plus, Server, Settings, Users, type LucideIcon } from 'lucide-react-native';
import { Pressable, View } from 'react-native';
import Animated, { FadeIn, LinearTransition } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { TAB_LABELS, type TabName } from '@/lib/roleTabs';
import { useTheme } from '@/theme/ThemeProvider';
import { fontFamily, radius } from '@/theme/tokens';

const ICONS: Record<TabName, LucideIcon> = {
  ozet: LayoutGrid,
  dosyalar: Folder,
  yeni: Plus,
  sistem: Server,
  kullanicilar: Users,
  ayarlar: Settings,
};

export function PillTabBar({ state, navigation, visible }: BottomTabBarProps & { visible: TabName[] }) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const routes = state.routes.filter((route) => visible.includes(route.name as TabName));
  const focusedName = state.routes[state.index]?.name;
  return (
    <View
      style={{
        position: 'absolute',
        left: 12,
        right: 12,
        bottom: Math.max(insets.bottom, 12),
        height: 64,
        borderRadius: radius.tab,
        backgroundColor: colors.deep,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 6,
      }}
    >
      {routes.map((route) => {
        const name = route.name as TabName;
        const focused = route.name === focusedName;
        const Icon = ICONS[name];
        return (
          <Animated.View key={route.key} layout={LinearTransition.springify().damping(16)} style={{ flex: focused ? 2.2 : 1 }}>
            <Pressable
              accessibilityRole="tab"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={TAB_LABELS[name]}
              onPress={() => {
                const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
                if (!focused && !event.defaultPrevented) navigation.navigate(route.name);
              }}
              style={{
                height: 44,
                borderRadius: 15,
                backgroundColor: focused ? colors.accent : 'transparent',
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
              }}
            >
              <Icon size={19} strokeWidth={2.2} color={focused ? colors.onAccent : 'rgba(255,255,255,0.55)'} />
              {focused && (
                <Animated.Text
                  entering={FadeIn.duration(200)}
                  numberOfLines={1}
                  style={{ fontFamily: fontFamily[700], fontSize: 12, color: colors.onAccent }}
                >
                  {TAB_LABELS[name]}
                </Animated.Text>
              )}
            </Pressable>
          </Animated.View>
        );
      })}
    </View>
  );
}
