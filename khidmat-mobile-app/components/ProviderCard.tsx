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
    <View className="mt-2 overflow-hidden rounded-2xl border border-gray-100 bg-white p-3.5 shadow-sm">
      {/* Header */}
      <View className="flex-row items-center justify-between">
        <View className="flex-row items-center flex-1 mr-2 min-w-0">
          <View className="h-10 w-10 items-center justify-center rounded-xl bg-primary-100/80 border border-primary-200/50 flex-shrink-0">
            <Text className="text-lg">
              {CATEGORY_EMOJI[provider.category] ?? '🛠'}
            </Text>
          </View>
          <View className="ml-2.5 flex-1 min-w-0">
            <View className="flex-row items-center">
              <Text className="text-[15px] font-bold text-gray-900 flex-shrink" numberOfLines={1} ellipsizeMode="tail">
                {provider.name}
              </Text>
              <Ionicons
                name="checkmark-circle"
                size={14}
                color="#16A34A"
                style={{ marginLeft: 3, flexShrink: 0 }}
              />
            </View>
            <Text className="text-xs font-medium text-gray-500" numberOfLines={1}>
              {CATEGORY_LABEL[provider.category] ?? provider.category}
            </Text>
          </View>
        </View>

        {/* Rating chip */}
        <View className="flex-row items-center rounded-full bg-amber-50 px-2 py-0.5 border border-amber-200/60 flex-shrink-0">
          <Ionicons name="star" size={11} color="#F59E0B" />
          <Text className="ml-1 text-xs font-bold text-amber-800">
            {provider.rating.toFixed(1)}
          </Text>
        </View>
      </View>

      {/* Stats row */}
      <View className="mt-2.5 flex-row items-center flex-wrap gap-1.5">
        <View className="flex-row items-center rounded-lg bg-gray-50 px-2 py-1 border border-gray-100">
          <Ionicons name="location-sharp" size={12} color="#6B7280" />
          <Text className="ml-1 text-xs font-medium text-gray-700">
            {distanceKm} km away
          </Text>
        </View>
        <View className="flex-row items-center rounded-lg bg-gray-50 px-2 py-1 border border-gray-100">
          <Ionicons name="chatbox-ellipses-outline" size={12} color="#6B7280" />
          <Text className="ml-1 text-xs font-medium text-gray-700">
            {provider.reviewCount > 0 ? `${provider.reviewCount} reviews` : 'Verified'}
          </Text>
        </View>
        <View className="rounded-lg bg-gray-50 px-2 py-1 border border-gray-100">
          <Text className="text-xs font-semibold text-gray-700">
            {provider.priceRange}
          </Text>
        </View>
      </View>

      {/* Suggested Slot Pill */}
      <View className="mt-2.5 rounded-xl bg-orange-50/80 border border-orange-200/60 px-3 py-2">
        <View className="flex-row items-center justify-between flex-wrap gap-1">
          <View className="flex-row items-center flex-shrink-0">
            <Ionicons name="time" size={13} color="#EA580C" />
            <Text className="ml-1.5 text-xs font-medium text-orange-950">
              Suggested Slot:
            </Text>
          </View>
          <Text className="text-xs font-bold text-primary-700 flex-shrink" numberOfLines={1} ellipsizeMode="tail">
            {dayLabel && dayLabel !== 'Scheduled' && !suggestedSlot.toLowerCase().includes(dayLabel.toLowerCase())
              ? `${dayLabel}, ${suggestedSlot}`
              : suggestedSlot}
          </Text>
        </View>
      </View>

      {/* AI Reasoning quote */}
      {reasoning ? (
        <View className="mt-2 flex-row items-start">
          <Ionicons
            name="sparkles-outline"
            size={12}
            color="#9CA3AF"
            style={{ marginTop: 2, marginRight: 4, flexShrink: 0 }}
          />
          <Text className="flex-1 text-xs leading-4 italic text-gray-500">
            {reasoning}
          </Text>
        </View>
      ) : null}

      {/* Book button */}
      <Pressable
        onPress={handleBookPress}
        className="mt-3 flex-row items-center justify-center rounded-xl bg-primary py-2.5 px-3 active:bg-primary-600 active:opacity-80 shadow-sm"
      >
        <Ionicons name="calendar-outline" size={15} color="#FFFFFF" style={{ marginRight: 6 }} />
        <Text className="text-[13px] font-bold text-white text-center" numberOfLines={1}>
          Book Appointment
        </Text>
      </Pressable>
    </View>
  );
}


