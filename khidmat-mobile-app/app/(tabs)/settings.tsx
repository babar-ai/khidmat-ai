import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  Pressable,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useSettingsStore } from '@/lib/stores/useSettingsStore';
import { useBookingsStore } from '@/lib/stores/useBookingsStore';
import { Button } from '@/components/Button';

const SECTOR_OPTIONS = [
  'F-6',
  'F-7',
  'F-8/1',
  'F-8/2',
  'F-10/1',
  'F-10/3',
  'F-11/1',
  'F-11/3',
  'G-9',
  'G-10',
  'G-11',
  'G-13',
  'I-8/3',
  'I-9',
];

export default function SettingsScreen() {
  const defaultLocation = useSettingsStore((s) => s.defaultLocation);
  const setDefaultLocation = useSettingsStore((s) => s.setDefaultLocation);
  const clearBookings = useBookingsStore((s) => s.clear);

  const [locationInput, setLocationInput] = useState(defaultLocation);
  const [showDropdown, setShowDropdown] = useState(false);

  const filteredSectors = useMemo(() => {
    if (!locationInput) return SECTOR_OPTIONS;
    return SECTOR_OPTIONS.filter((s) =>
      s.toLowerCase().includes(locationInput.toLowerCase()),
    );
  }, [locationInput]);

  const handleLocationChange = (text: string) => {
    setLocationInput(text);
    setShowDropdown(true);
    // Save deferred — only commit valid sectors on blur or select
  };

  const handleSectorSelect = (sector: string) => {
    setLocationInput(sector);
    setDefaultLocation(sector);
    setShowDropdown(false);
  };

  const handleBlur = () => {
    // Delay so onPress on the dropdown can fire first
    setTimeout(() => {
      setShowDropdown(false);
      const trimmed = locationInput.trim();
      const matched = SECTOR_OPTIONS.find(
        (s) => s.toLowerCase() === trimmed.toLowerCase(),
      );
      if (matched) {
        setDefaultLocation(matched);
        setLocationInput(matched);
      } else {
        // Invalid entry — revert to the last saved value
        setLocationInput(defaultLocation);
      }
    }, 200);
  };

  const handleClearBookings = () => {
    Alert.alert(
      'Clear All Bookings',
      'This will permanently delete all your bookings. Are you sure?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: () => clearBookings(),
        },
      ],
    );
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <View className="border-b border-gray-50 px-5 pb-3 pt-4">
        <Text className="text-lg font-bold text-gray-900">Settings</Text>
      </View>

      <ScrollView
        className="flex-1 px-5 pt-5"
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {/* Section 1: Default Location */}
        <View className="mb-6">
          <Text className="mb-2 text-sm font-bold text-gray-900">
            Your default location
          </Text>
          <TextInput
            className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-[15px] text-gray-900"
            value={locationInput}
            onChangeText={handleLocationChange}
            onFocus={() => setShowDropdown(true)}
            onBlur={handleBlur}
            placeholder="e.g. F-10/3"
            placeholderTextColor="#9CA3AF"
            autoCapitalize="characters"
            autoCorrect={false}
          />

          {/* Dropdown */}
          {showDropdown && filteredSectors.length > 0 && (
            <View className="mt-1 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
              {filteredSectors.map((sector) => (
                <Pressable
                  key={sector}
                  onPress={() => handleSectorSelect(sector)}
                  className="border-b border-gray-50 px-4 py-3 active:bg-gray-50"
                >
                  <Text
                    className={`text-sm ${
                      sector === locationInput
                        ? 'font-bold text-primary'
                        : 'text-gray-700'
                    }`}
                  >
                    {sector}
                  </Text>
                </Pressable>
              ))}
            </View>
          )}

          <Text className="mt-2 text-xs text-gray-400">
            Used when you don&apos;t specify a location in your request.
          </Text>
        </View>

        {/* Section 2: About */}
        <View className="mb-6 rounded-2xl bg-primary-50 p-4">
          <Text className="mb-2 text-sm font-bold text-gray-900">
            About Khidmat
          </Text>
          <Text className="text-[13px] leading-5 text-gray-600">
            Khidmat is an AI-powered service orchestrator. Tell me what you need
            in natural language — I&apos;ll find the right provider, book the
            slot, and follow up.
          </Text>
        </View>

        {/* Section 3: Clear bookings */}
        <View className="mb-8">
          <Button variant="destructive" onPress={handleClearBookings}>
            Clear all bookings
          </Button>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
