import {
  Geist_400Regular,
  Geist_500Medium,
  Geist_600SemiBold,
  Geist_700Bold,
  Geist_800ExtraBold,
  useFonts,
} from '@expo-google-fonts/geist';
import { GeistMono_400Regular, GeistMono_500Medium } from '@expo-google-fonts/geist-mono';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { shouldRetryQuery } from '@/api/retry';
import { ServerUrlProvider } from '@/api/ServerUrlProvider';
import { AuthProvider, useAuth } from '@/auth/AuthProvider';
import { BaglantiHatasi } from '@/features/baglanti/BaglantiHatasi';
import { canViewPatients } from '@/lib/roleTabs';
import { ThemeProvider, useTheme } from '@/theme/ThemeProvider';

SplashScreen.preventAutoHideAsync();

function RootNavigator() {
  const { status, user } = useAuth();
  const { colors, name } = useTheme();

  useEffect(() => {
    if (status !== 'yukleniyor') SplashScreen.hideAsync();
  }, [status]);

  if (status === 'yukleniyor') return null;
  if (status === 'baglanti_hatasi') return <BaglantiHatasi />;

  const signedIn = status === 'girisli' && user !== null;
  return (
    <>
      <StatusBar style={name === 'dark' ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.bg } }}>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="giris" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn}>
          <Stack.Screen name="(tabs)" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn && canViewPatients(user!.rol)}>
          <Stack.Screen name="dosya/[id]" options={{ animation: 'slide_from_right' }} />
        </Stack.Protected>
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Geist_400Regular,
    Geist_500Medium,
    Geist_600SemiBold,
    Geist_700Bold,
    Geist_800ExtraBold,
    GeistMono_400Regular,
    GeistMono_500Medium,
  });
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: shouldRetryQuery,
          },
        },
      }),
  );
  if (!fontsLoaded) return null;
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <QueryClientProvider client={queryClient}>
            <ServerUrlProvider>
              <AuthProvider>
                <RootNavigator />
              </AuthProvider>
            </ServerUrlProvider>
          </QueryClientProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
