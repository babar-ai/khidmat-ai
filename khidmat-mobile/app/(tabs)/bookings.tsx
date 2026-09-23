import React, { useCallback, useMemo, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  Pressable,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';

import { StatusBadge } from '@/components/StatusBadge';
import { useBookingsStore } from '@/lib/stores/useBookingsStore';

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

export default function BookingsScreen() {
  const rawBookings = useBookingsStore((s) => s.bookings);
  const bookings = useMemo(
    () => [...rawBookings].sort((a, b) => b.createdAt - a.createdAt),
    [rawBookings],
  );
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    // Simulate a brief refresh
    setTimeout(() => setRefreshing(false), 600);
  }, []);

  if (bookings.length === 0) {
    return (
      <SafeAreaView className="flex-1 bg-white" edges={['top']}>
        <View className="border-b border-gray-50 px-5 pb-3 pt-4">
          <Text className="text-lg font-bold text-gray-900">Bookings</Text>
        </View>
        <View className="flex-1 items-center justify-center px-8">
          <Text className="text-5xl">📋</Text>
          <Text className="mt-4 text-lg font-semibold text-gray-700">
            No bookings yet
          </Text>
          <Text className="mt-1 text-center text-sm text-gray-400">
            Start a conversation to book a service provider
          </Text>
          <Pressable
            onPress={() => router.push('/(tabs)')}
            className="mt-5 rounded-2xl bg-primary-50 px-6 py-2.5 active:bg-primary-100"
          >
            <Text className="text-sm font-semibold text-primary">
              Go to Chat
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <View className="border-b border-gray-50 px-5 pb-3 pt-4">
        <Text className="text-lg font-bold text-gray-900">Bookings</Text>
        <Text className="text-xs text-gray-400">
          {bookings.length} booking{bookings.length !== 1 ? 's' : ''}
        </Text>
      </View>
      <ScrollView
        className="flex-1 px-4 pt-3"
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#F97316"
            colors={['#F97316']}
          />
        }
      >
        {bookings.map((booking) => (
          <Pressable
            key={booking.id}
            onPress={() => router.push(`/bookings/${booking.id}`)}
            className="mb-3 flex-row items-center rounded-2xl border border-gray-100 bg-white p-4 shadow-sm active:bg-gray-50"
          >
            {/* Category emoji */}
            <View className="h-11 w-11 items-center justify-center rounded-full bg-primary-50">
              <Text className="text-xl">
                {CATEGORY_EMOJI[booking.category] ?? '🛠'}
              </Text>
            </View>

            {/* Info */}
            <View className="ml-3 flex-1">
              <Text className="text-[15px] font-bold text-gray-900">
                {booking.providerName}
              </Text>
              <Text className="mt-0.5 text-xs text-gray-500">
                {CATEGORY_LABEL[booking.category] ?? booking.category} ·{' '}
                {booking.sector}
              </Text>
              <Text className="mt-0.5 text-xs text-gray-400">
                {booking.scheduledFor}
              </Text>
            </View>

            {/* Status badge */}
            <StatusBadge status={booking.status} />
          </Pressable>
        ))}
        <View className="h-6" />
      </ScrollView>
    </SafeAreaView>
  );
}
