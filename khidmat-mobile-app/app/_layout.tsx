import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { KeyboardProvider } from 'react-native-keyboard-controller';

import { useLocationStore } from '@/lib/stores/useLocationStore';
import '../global.css';

/**
 * RootLayout — runs once when the app starts.
 *
 * On mount, triggers requestLocationPermission() from the location store:
 *   • Prompts the user for GPS permission via the Android/iOS system dialog.
 *   • On grant: stores latitude + longitude in useLocationStore.
 *   • On deny: stores 'denied' status; app still works with city-wide fallback.
 *
 * The coordinates are then automatically attached to every POST /api/v1/request
 * call by the API client (lib/api/khidmatApi.ts).
 */
export default function RootLayout() {
  const requestLocationPermission = useLocationStore((s) => s.requestLocationPermission);

  useEffect(() => {
    // Request GPS permission and capture initial fix immediately on app start
    requestLocationPermission();
  }, [requestLocationPermission]);

  return (
    <KeyboardProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: '#FFFFFF' },
        }}
      >
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="bookings/[id]"
          options={{
            headerShown: false,
          }}
        />
      </Stack>
    </KeyboardProvider>
  );
}
