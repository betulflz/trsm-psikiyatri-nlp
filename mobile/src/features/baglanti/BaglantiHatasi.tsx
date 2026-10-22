import { useState } from 'react';
import { View } from 'react-native';
import { ApiError } from '@/api/errors';
import { useServerUrl } from '@/api/ServerUrlProvider';
import { useAuth } from '@/auth/AuthProvider';
import { Button, ErrorState, Screen } from '@/ui';
import { SunucuAdresi } from './SunucuAdresi';

export function BaglantiHatasi() {
  const { url } = useServerUrl();
  const { retry, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  return (
    <Screen>
      <View style={{ flex: 1, justifyContent: 'center', gap: 16, paddingTop: 80 }}>
        <ErrorState error={new ApiError('ag', null, '')} onRetry={retry} />
        {editing ? (
          <SunucuAdresi
            onSaved={() => {
              setEditing(false);
              retry();
            }}
          />
        ) : (
          <Button title={`Adresi değiştir (${url})`} variant="ghost" onPress={() => setEditing(true)} />
        )}
        <Button title="Çıkış yap" variant="ghost" onPress={logout} />
      </View>
    </Screen>
  );
}
