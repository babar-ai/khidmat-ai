import React from 'react';
import { View, Text, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
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
  const handleBookPress = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onBook();
  };

  return (
    <View className="mt-2.5 overflow-hidden rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
      {/* Header */}
      <View className="flex-row items-center justify-between">
        <View className="flex-row items-center flex-1">
          <View className="h-11 w-11 items-center justify-center rounded-2xl bg-primary-100/80 border border-primary-200/50">
            <Text className="text-xl">
              {CATEGORY_EMOJI[provider.category] ?? '🛠'}
            </Text>
          </View>
          <View className="ml-3 flex-1">
            <View className="flex-row items-center">
              <Text className="text-base font-bold text-gray-900" numberOfLines={1}>
                {provider.name}
              </Text>
              <Ionicons
                name="checkmark-circle"
                size={15}
                color="#16A34A"
                style={{ marginLeft: 4 }}
              />
            </View>
            <Text className="text-xs font-medium text-gray-500">
              {CATEGORY_LABEL[provider.category] ?? provider.category}
            </Text>
          </View>
        </View>

        {/* Rating chip */}
        <View className="flex-row items-center rounded-full bg-amber-50 px-2.5 py-1 border border-amber-200/60">
          <Ionicons name="star" size={12} color="#F59E0B" />
          <Text className="ml-1 text-xs font-bold text-amber-800">
            {provider.rating.toFixed(1)}
          </Text>
        </View>
      </View>

      {/* Stats row */}
      <View className="mt-3 flex-row items-center gap-2">
        <View className="flex-row items-center rounded-lg bg-gray-50 px-2.5 py-1">
          <Ionicons name="location-sharp" size={13} color="#6B7280" />
          <Text className="ml-1 text-xs font-medium text-gray-700">
            {distanceKm} km away
          </Text>
        </View>
        <View className="flex-row items-center rounded-lg bg-gray-50 px-2.5 py-1">
          <Ionicons name="chatbox-ellipses-outline" size={13} color="#6B7280" />
          <Text className="ml-1 text-xs font-medium text-gray-700">
            {provider.reviewCount > 0 ? `${provider.reviewCount} reviews` : 'Verified'}
          </Text>
        </View>
        <View className="ml-auto">
          <Text className="text-xs font-semibold text-gray-700">
            {provider.priceRange}
          </Text>
        </View>
      </View>

      {/* Suggested Slot Pill */}
      <View className="mt-3 flex-row items-center justify-between rounded-xl bg-orange-50/70 border border-orange-100 px-3 py-2">
        <View className="flex-row items-center">
          <Ionicons name="time" size={14} color="#EA580C" />
          <Text className="ml-1.5 text-xs font-medium text-orange-950">
            Suggested Slot:
          </Text>
        </View>
        <Text className="text-xs font-bold text-primary-700">
          {dayLabel}, {suggestedSlot}
        </Text>
      </View>

      {/* AI Reasoning quote */}
      {reasoning ? (
        <View className="mt-2.5 flex-row items-start">
          <Ionicons
            name="sparkles-outline"
            size={12}
            color="#9CA3AF"
            style={{ marginTop: 2, marginRight: 4 }}
          />
          <Text className="flex-1 text-xs leading-4 italic text-gray-500">
            {reasoning}
          </Text>
        </View>
      ) : null}

      {/* Book button */}
      <Pressable
        onPress={handleBookPress}
        className="mt-3.5 flex-row items-center justify-center rounded-xl bg-primary py-3 active:bg-primary-600 active:opacity-80 shadow-sm"
      >
        <Ionicons name="calendar-outline" size={16} color="#FFFFFF" style={{ marginRight: 6 }} />
        <Text className="text-[14px] font-bold text-white">
          Book Appointment ({dayLabel})
        </Text>
      </Pressable>
    </View>
  );
}


