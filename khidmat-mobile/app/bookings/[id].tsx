import React, { useState, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Alert,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

import { StatusBadge } from '@/components/StatusBadge';
import { ChatBubble } from '@/components/ChatBubble';
import { ExtractedFieldsRow } from '@/components/ExtractedFieldsRow';
import { Button } from '@/components/Button';
import { useBookingsStore } from '@/lib/stores/useBookingsStore';
import { providers } from '@/lib/mock/providers';
import type { AgentEvent } from '@/lib/agent/types';

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

// ── Status Timeline ─────────────────────────────────────────────

const TIMELINE_STEPS = [
  { key: 'confirmed', label: 'Confirmed', icon: 'checkmark-circle' as const },
  {
    key: 'reminded',
    label: 'Reminder scheduled',
    icon: 'alarm' as const,
  },
  {
    key: 'completed',
    label: 'Completed',
    icon: 'checkmark-done-circle' as const,
  },
];

function getStepIndex(status: string): number {
  if (status === 'cancelled') return -1;
  const idx = TIMELINE_STEPS.findIndex((s) => s.key === status);
  return idx >= 0 ? idx : 0;
}

export default function BookingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const bookings = useBookingsStore((s) => s.bookings);
  const booking = useMemo(
    () => bookings.find((b) => b.id === id),
    [bookings, id],
  );
  const cancel = useBookingsStore((s) => s.cancel);
  const updateStatus = useBookingsStore((s) => s.updateStatus);
  const [showThread, setShowThread] = useState(false);

  const provider = providers.find((p) => p.id === booking?.providerId);

  const handleCancel = useCallback(() => {
    Alert.alert(
      'Cancel Booking',
      'Are you sure you want to cancel this booking?',
      [
        { text: 'Keep it', style: 'cancel' },
        {
          text: 'Cancel Booking',
          style: 'destructive',
          onPress: () => {
            if (id) {
              cancel(id);
              router.back();
            }
          },
        },
      ],
    );
  }, [id, cancel]);

  const handleMarkCompleted = useCallback(() => {
    if (!id) return;
    Alert.alert('Mark as Completed', 'Service is done? This marks the booking complete.', [
      { text: 'Not yet', style: 'cancel' },
      {
        text: 'Mark Completed',
        onPress: () => updateStatus(id, 'completed'),
      },
    ]);
  }, [id, updateStatus]);

  const handleCall = useCallback(() => {
    if (provider?.phone) {
      Linking.openURL(`tel:${provider.phone}`);
    }
  }, [provider]);

  if (!booking) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-white" edges={['top']}>
        <Text className="text-gray-400">Booking not found</Text>
      </SafeAreaView>
    );
  }

  const currentStep = getStepIndex(booking.status);

  // ── Render a thread event (simplified) ───────────────────

  const renderThreadEvent = (event: AgentEvent, index: number) => {
    switch (event.type) {
      case 'understanding':
        return (
          <ChatBubble key={index} side="agent">
            <Text className="text-sm text-gray-900">
              Got it, here&apos;s what I understood:
            </Text>
            <ExtractedFieldsRow
              service={
                event.extracted.service
                  ? CATEGORY_LABEL[event.extracted.service] ??
                    event.extracted.service
                  : null
              }
              location={
                event.usedDefaultLocation
                  ? `${event.extracted.location} (your home)`
                  : event.extracted.location
              }
              time={event.extracted.time}
            />
          </ChatBubble>
        );
      case 'searching':
        return (
          <ChatBubble key={index} side="agent">
            <Text className="text-sm text-gray-900">
              Looking for {CATEGORY_LABEL[event.category] ?? event.category}{' '}
              near {event.near}...
            </Text>
          </ChatBubble>
        );
      case 'ranking':
        return (
          <ChatBubble key={index} side="agent">
            <Text className="text-sm text-gray-900">
              Found {event.candidateCount} nearby. Ranked by distance, rating,
              and availability.
            </Text>
          </ChatBubble>
        );
      case 'recommendation':
        return (
          <ChatBubble key={index} side="agent">
            <Text className="text-sm text-gray-900">
              Recommended {event.provider.name} — {event.reasoning}
            </Text>
          </ChatBubble>
        );
      case 'confirmed':
        return (
          <ChatBubble key={index} side="agent" tone="success">
            <Text className="text-sm font-semibold text-green-900">
              ✅ Booking confirmed
            </Text>
          </ChatBubble>
        );
      case 'reminder_scheduled':
        return (
          <ChatBubble key={index} side="agent">
            <Text className="text-sm text-gray-900">
              ⏰ Reminder at {event.at}
            </Text>
          </ChatBubble>
        );
      default:
        return null;
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      {/* Custom header — avoids edge-to-edge overlap on Android */}
      <View className="flex-row items-center border-b border-gray-50 px-4 pb-3 pt-2">
        <Pressable
          onPress={() => router.back()}
          className="mr-3 h-9 w-9 items-center justify-center rounded-full active:bg-gray-100"
        >
          <Ionicons name="arrow-back" size={22} color="#F97316" />
        </Pressable>
        <Text className="text-lg font-bold text-gray-900">
          Booking Details
        </Text>
      </View>

      <ScrollView
        className="flex-1 bg-white px-5 pt-4"
        showsVerticalScrollIndicator={false}
      >
      {/* Provider Header */}
      <View className="items-center pb-4">
        <View className="mb-3 h-16 w-16 items-center justify-center rounded-full bg-primary-100">
          <Text className="text-3xl">
            {CATEGORY_EMOJI[booking.category] ?? '🛠'}
          </Text>
        </View>
        <Text className="text-xl font-bold text-gray-900">
          {booking.providerName}
        </Text>
        <Text className="mt-1 text-sm text-gray-500">
          {CATEGORY_LABEL[booking.category] ?? booking.category}
        </Text>
        <View className="mt-2">
          <StatusBadge status={booking.status} />
        </View>
      </View>

      {/* Booking Info */}
      <View className="mb-4 rounded-2xl border border-gray-100 bg-gray-50 p-4">
        <View className="mb-3 flex-row items-center">
          <Ionicons name="time-outline" size={18} color="#6b7280" />
          <Text className="ml-2 text-sm text-gray-700">
            {booking.scheduledFor}
          </Text>
        </View>
        <View className="mb-3 flex-row items-center">
          <Ionicons name="location-outline" size={18} color="#6b7280" />
          <Text className="ml-2 text-sm text-gray-700">{booking.sector}</Text>
        </View>
        {provider?.phone && (
          <Pressable
            onPress={handleCall}
            className="flex-row items-center active:opacity-60"
          >
            <Ionicons name="call-outline" size={18} color="#F97316" />
            <Text className="ml-2 text-sm font-medium text-primary">
              {provider.phone}
            </Text>
          </Pressable>
        )}
      </View>

      {/* Agent Thread (collapsible) */}
      <Pressable
        onPress={() => setShowThread((v) => !v)}
        className="mb-2 flex-row items-center justify-between rounded-2xl border border-gray-100 bg-white px-4 py-3"
      >
        <Text className="text-sm font-bold text-gray-900">
          Why I picked this provider
        </Text>
        <Ionicons
          name={showThread ? 'chevron-up' : 'chevron-down'}
          size={18}
          color="#9CA3AF"
        />
      </Pressable>

      {showThread && (
        <View className="mb-4 rounded-2xl bg-gray-50 p-3">
          {booking.agentThread.map((event, i) => renderThreadEvent(event, i))}
        </View>
      )}

      {/* Status Timeline */}
      <View className="mb-6 rounded-2xl border border-gray-100 bg-white p-4">
        <Text className="mb-4 text-sm font-bold text-gray-900">
          Status Timeline
        </Text>
        {TIMELINE_STEPS.map((step, idx) => {
          const isActive = idx <= currentStep && booking.status !== 'cancelled';
          const isCurrent = idx === currentStep && booking.status !== 'cancelled';
          return (
            <View key={step.key} className="flex-row">
              {/* Line + Circle */}
              <View className="items-center" style={{ width: 32 }}>
                <View
                  className={`h-7 w-7 items-center justify-center rounded-full ${
                    isActive ? 'bg-primary' : 'bg-gray-200'
                  }`}
                >
                  <Ionicons
                    name={step.icon}
                    size={16}
                    color={isActive ? '#FFFFFF' : '#9CA3AF'}
                  />
                </View>
                {idx < TIMELINE_STEPS.length - 1 && (
                  <View
                    className={`h-8 w-0.5 ${
                      isActive ? 'bg-primary-300' : 'bg-gray-200'
                    }`}
                  />
                )}
              </View>
              {/* Label */}
              <View className="ml-3 justify-center pb-5">
                <Text
                  className={`text-sm ${
                    isCurrent
                      ? 'font-bold text-primary'
                      : isActive
                        ? 'font-medium text-gray-700'
                        : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </Text>
              </View>
            </View>
          );
        })}

        {booking.status === 'cancelled' && (
          <View className="mt-2 flex-row items-center rounded-xl bg-red-50 px-3 py-2">
            <Ionicons name="close-circle" size={16} color="#DC2626" />
            <Text className="ml-2 text-sm font-medium text-red-600">
              This booking was cancelled
            </Text>
          </View>
        )}
      </View>

      {/* Actions */}
      {(booking.status === 'confirmed' || booking.status === 'reminded') && (
        <View className="mb-12 gap-3">
          <Button variant="primary" onPress={handleMarkCompleted}>
            Mark as completed
          </Button>
          <Button variant="destructive" onPress={handleCancel}>
            Cancel booking
          </Button>
        </View>
      )}

      <View className="h-8" />
      </ScrollView>
    </SafeAreaView>
  );
}
