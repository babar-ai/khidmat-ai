import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { KeyboardProvider } from 'react-native-keyboard-controller';

import '../global.css';

export default function RootLayout() {
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
