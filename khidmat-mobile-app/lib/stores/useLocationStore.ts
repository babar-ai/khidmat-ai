/**
 * Location store for Khidmat AI mobile app.
 *
 * Manages GPS permission request on app launch and stores the device
 * coordinates globally so they can be attached to every API request.
 *
 * Location Priority (mirrors backend matching_node):
 *   Tier 1 — Nominatim geocodes extracted text address (done on backend)
 *   Tier 2 — Device GPS (user_lat / user_lng) — THIS store provides this
 *   Tier 3 — No coordinates → backend falls back to city-wide ranking
 */
import * as Location from 'expo-location';
import { create } from 'zustand';

type Coordinates = {
  latitude: number;
  longitude: number;
} | null;

type LocationState = {
  // Current GPS fix from the device
  coordinates: Coordinates;

  // Permission status
  permissionStatus: 'unknown' | 'granted' | 'denied';

  // Whether we are currently fetching the GPS fix
  isFetching: boolean;

  // Human-readable error if location fetch fails
  locationError: string | null;

  // Actions
  requestLocationPermission: () => Promise<void>;
  clearError: () => void;
};

export const useLocationStore = create<LocationState>((set) => ({
  coordinates: null,
  permissionStatus: 'unknown',
  isFetching: false,
  locationError: null,

  /**
   * Call this once on app startup (from RootLayout / _layout.tsx).
   *
   * Flow:
   *  1. Ask Android/iOS for foreground location permission
   *  2. If granted → get a high-accuracy GPS fix and store it
   *  3. If denied → store 'denied', app still works (Tier 3 fallback)
   */
  requestLocationPermission: async () => {
    set({ isFetching: true, locationError: null });

    try {
      // Step 1: Request permission
      const { status } = await Location.requestForegroundPermissionsAsync();

      if (status !== 'granted') {
        set({
          permissionStatus: 'denied',
          isFetching: false,
          locationError: 'Location permission denied. Provider ranking will use city-wide results.',
        });
        return;
      }

      set({ permissionStatus: 'granted' });

      // Step 2: Get current GPS fix (high accuracy = real GPS chip, not WiFi/cell)
      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });

      set({
        coordinates: {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        },
        isFetching: false,
        locationError: null,
      });
    } catch (error) {
      set({
        isFetching: false,
        locationError: 'Could not determine your location. Showing nearest providers by rating.',
      });
    }
  },

  clearError: () => set({ locationError: null }),
}));
