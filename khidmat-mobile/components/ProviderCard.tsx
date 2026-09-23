import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { Provider } from '@/lib/mock/providers';

type ProviderCardProps = {
  provider: Provider;
  distanceKm: number;
  reasoning: string;
  suggestedSlot: string;
  dayLabel: string;
  onBook: () => void;
};

const CATEGORY_EMOJI: Record<string, string> = {
  ac: '❄️',
  plumber: '🔧',
  electrician: '⚡',
  tutor: '📚',
  beautician: '💅',
};

const CATEGORY_LABEL: Record<string, string> = {
  ac: 'AC Repair',
  plumber: 'Plumbing',
  electrician: 'Electrical',
  tutor: 'Tutoring',
  beautician: 'Beauty',
};

export function ProviderCard({
  provider,
  distanceKm,
  reasoning,
  suggestedSlot,
  dayLabel,
  onBook,
}: ProviderCardProps) {
  return (
    <View className="mt-2 overflow-hidden rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
      {/* Header */}
      <View className="flex-row items-center">
        <View className="h-10 w-10 items-center justify-center rounded-full bg-primary-100">
          <Text className="text-lg">
            {CATEGORY_EMOJI[provider.category] ?? '🛠'}
          </Text>
        </View>
        <View className="ml-3 flex-1">
          <Text className="text-base font-bold text-gray-900">
            {provider.name}
          </Text>
          <Text className="text-xs text-gray-500">
            {CATEGORY_LABEL[provider.category] ?? provider.category}
          </Text>
        </View>
      </View>

      {/* Stats row */}
      <View className="mt-3 flex-row items-center gap-3">
        <View className="flex-row items-center">
          <Ionicons name="location-outline" size={14} color="#6b7280" />
          <Text className="ml-1 text-xs text-gray-600">
            {distanceKm} km away
          </Text>
        </View>
        <View className="flex-row items-center">
          <Text className="text-xs text-yellow-500">★</Text>
          <Text className="ml-0.5 text-xs font-semibold text-gray-700">
            {provider.rating}
          </Text>
          <Text className="ml-1 text-xs text-gray-400">
            · {provider.reviewCount} reviews
          </Text>
        </View>
      </View>

      {/* Price + slot */}
      <View className="mt-2 flex-row items-center justify-between">
        <Text className="text-xs font-medium text-gray-500">
          {provider.priceRange}
        </Text>
        <View className="flex-row items-center rounded-full bg-primary-50 px-2.5 py-1">
          <Ionicons name="time-outline" size={12} color="#EA580C" />
          <Text className="ml-1 text-xs font-semibold text-primary-700">
            {dayLabel}, {suggestedSlot}
          </Text>
        </View>
      </View>

      {/* Reasoning */}
      <Text className="mt-2 text-xs italic text-gray-400">{reasoning}</Text>

      {/* Book button */}
      <Pressable
        onPress={onBook}
        className="mt-3 items-center rounded-xl bg-primary py-3 active:bg-primary-600"
      >
        <Text className="text-sm font-bold text-white">
          Book {dayLabel} at {suggestedSlot}
        </Text>
      </Pressable>
    </View>
  );
}
