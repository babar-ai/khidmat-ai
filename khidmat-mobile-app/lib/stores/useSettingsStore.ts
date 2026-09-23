import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

type SettingsState = {
  defaultLocation: string;
  setDefaultLocation: (location: string) => void;
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      defaultLocation: 'F-10/3',
      setDefaultLocation: (location: string) =>
        set({ defaultLocation: location }),
    }),
    {
      name: 'khidmat-settings',
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
