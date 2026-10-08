import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  Platform,
  Animated,
  Alert,
  Pressable,
} from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

import { ChatBubble } from '@/components/ChatBubble';
import { ExtractedFieldsRow } from '@/components/ExtractedFieldsRow';
import { ProviderCard } from '@/components/ProviderCard';
import { InputBar } from '@/components/InputBar';
import { ExamplePromptChip } from '@/components/ExamplePromptChip';
import { runAgent, confirmBooking, resetConversationSession } from '@/lib/agent/realAgent';
import { useSettingsStore } from '@/lib/stores/useSettingsStore';
import { useBookingsStore } from '@/lib/stores/useBookingsStore';
import { useLocationStore } from '@/lib/stores/useLocationStore';
import type { AgentEvent } from '@/lib/agent/types';

type RecommendationEvent = Extract<AgentEvent, { type: 'recommendation' }>;

// ── Types for chat messages ─────────────────────────────────────

type ChatMessage =
  | { id: string; role: 'user'; text: string; timestamp: string }
  | { id: string; role: 'agent'; event: AgentEvent; timestamp: string };

function formatCurrentTime(): string {
  const now = new Date();
  return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ── Animated wrapper for smooth fade-in + slide-up ──────────────

function FadeInSlide({ children }: { children: React.ReactNode }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(10)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.spring(translateY, {
        toValue: 0,
        tension: 80,
        friction: 8,
        useNativeDriver: true,
      }),
    ]).start();
  }, [opacity, translateY]);

  return (
    <Animated.View style={{ opacity, transform: [{ translateY }] }}>
      {children}
    </Animated.View>
  );
}

// ── Smooth Dots Loader ──────────────────────────────────────────

function DotsLoader() {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animate = (dot: Animated.Value, delay: number) => {
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(dot, {
            toValue: 1,
            duration: 320,
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 320,
            useNativeDriver: true,
          }),
        ]),
      ).start();
    };
    animate(dot1, 0);
    animate(dot2, 160);
    animate(dot3, 320);
  }, [dot1, dot2, dot3]);

  return (
    <View className="flex-row items-center gap-1.5 py-0.5">
      {[dot1, dot2, dot3].map((dot, i) => (
        <Animated.View
          key={i}
          style={{
            opacity: dot.interpolate({ inputRange: [0, 1], outputRange: [0.35, 1] }),
            transform: [
              {
                translateY: dot.interpolate({ inputRange: [0, 1], outputRange: [0, -3] }),
              },
              {
                scale: dot.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1.15] }),
              },
            ],
          }}
          className="h-2 w-2 rounded-full bg-primary"
        />
      ))}
    </View>
  );
}

// ── Typing indicator matching agent response box style ─────────

function TypingIndicator() {
  return (
    <View className="mb-3 flex-row items-end">
      <View className="mr-2 mb-1 h-7 w-7 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
        <Ionicons name="sparkles" size={14} color="#F97316" />
      </View>
      <View className="rounded-2xl rounded-bl-xs bg-gray-100 px-4 py-3 flex-row items-center">
        <DotsLoader />
        <Text className="ml-2.5 text-xs font-medium text-gray-500">
          Khidmat AI is thinking...
        </Text>
      </View>
    </View>
  );
}

// ── Category display names ──────────────────────────────────────

const CATEGORY_LABEL: Record<string, string> = {
  ac: 'AC Technician',
  plumber: 'Plumber',
  electrician: 'Electrician',
  tutor: 'Tutor',
  beautician: 'Beautician',
};

// ── Quick Category Shortcuts for Empty State ────────────────────

const SERVICE_SHORTCUTS = [
  { label: 'AC Repair', icon: '❄️', prompt: 'Mujhe AC technician chahiye Islamabad mein' },
  { label: 'Plumber', icon: '🔧', prompt: 'Bathroom leak fix karne ke liye plumber chahiye' },
  { label: 'Electrician', icon: '⚡', prompt: 'Wiring aur short circuit check karne ke liye electrician chahiye' },
  { label: 'Cleaner', icon: '🧹', prompt: 'Deep home cleaning service chahiye' },
  { label: 'Carpenter', icon: '🔨', prompt: 'Furniture repair ke liye carpenter chahiye' },
  { label: 'Painter', icon: '🎨', prompt: 'Room wall painting ke liye painter chahiye' },
];

const EXAMPLE_PROMPTS = [
  { text: 'Mujhe kal subah G-13 mein AC technician chahiye', icon: '❄️' },
  { text: 'Plumber abhi chahiye, bathroom pipe leak hai', icon: '🔧' },
  { text: 'Ghar ke wiring check ke liye electrician chahiye', icon: '⚡' },
  { text: 'Beautician chahiye Sunday ko, home service', icon: '💅' },
];

// ── Main Chat Screen ────────────────────────────────────────────

export default function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState<RecommendationEvent | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const scrollRef = useRef<ScrollView>(null);
  const agentEventsRef = useRef<AgentEvent[]>([]);

  const insets = useSafeAreaInsets();
  const defaultLocation = useSettingsStore((s) => s.defaultLocation);
  const addBooking = useBookingsStore((s) => s.addBooking);
  const rescheduleBooking = useBookingsStore((s) => s.rescheduleBooking);

  // GPS location state
  const { coordinates, permissionStatus, isFetching, requestLocationPermission } =
    useLocationStore();
  const hasGps = coordinates !== null;

  const scrollToBottom = useCallback((delay = 80) => {
    setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, delay);
  }, []);

  const addAgentMessage = useCallback(
    (event: AgentEvent) => {
      // Retain internal booking state tracking without displaying confirmation card in chat UI
      setAgentEvents((prev) => {
        const next = [...prev, event];
        agentEventsRef.current = next;
        return next;
      });

      if (event.type === 'understanding') {
        return;
      }

      const msg: ChatMessage = {
        id: `agent_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        role: 'agent',
        event,
        timestamp: formatCurrentTime(),
      };
      setMessages((prev) => [...prev, msg]);
      if (event.type === 'confirmed') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
      scrollToBottom();
    },
    [scrollToBottom],
  );

  const handleSend = useCallback(
    async (textToSend?: string) => {
      const text = (textToSend ?? inputText).trim();
      if (!text || isProcessing || isConfirming) return;

      if (pendingConfirmation) {
        setPendingConfirmation(null);
      }

      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      setInputText('');
      setIsProcessing(true);

      // Add user message
      const userMsg: ChatMessage = {
        id: `user_${Date.now()}`,
        role: 'user',
        text,
        timestamp: formatCurrentTime(),
      };
      setMessages((prev) => [...prev, userMsg]);
      scrollToBottom();

      // Run agent
      try {
        const gen = runAgent(text, {
          defaultLocation,
          conversationHistory: agentEventsRef.current,
        });

        const flowEvents: AgentEvent[] = [];
        for await (const event of gen) {
          addAgentMessage(event);
          flowEvents.push(event);
        }

        const confirmedEvent = flowEvents.find(
          (e): e is Extract<AgentEvent, { type: 'confirmed' }> => e.type === 'confirmed',
        );
        const recEvent = flowEvents.find(
          (e): e is RecommendationEvent => e.type === 'recommendation',
        );
        const reminderEvent = flowEvents.find(
          (e): e is Extract<AgentEvent, { type: 'reminder_scheduled' }> =>
            e.type === 'reminder_scheduled',
        );

        if (confirmedEvent && recEvent) {
          addBooking({
            id: confirmedEvent.bookingId,
            providerId: recEvent.provider.id,
            providerName: recEvent.provider.name,
            category: recEvent.provider.category,
            sector: recEvent.provider.sector,
            scheduledFor: `${recEvent.dayLabel}, ${recEvent.suggestedSlot}`,
            scheduledTimestamp: recEvent.scheduledTimestamp,
            status: 'confirmed',
            reminderAt: reminderEvent?.at ?? '1 hour before',
            agentThread: [...agentEventsRef.current],
            createdAt: Date.now(),
          });
        }

        const rescheduleEvent = flowEvents.find(
          (e): e is Extract<AgentEvent, { type: 'rescheduled' }> => e.type === 'rescheduled',
        );
        if (rescheduleEvent) {
          rescheduleBooking(rescheduleEvent.bookingId, rescheduleEvent.newSlot);
        }

        // If the agent requested explicit confirmation, activate confirmation UI
        const confirmRequestEvent = flowEvents.find(
          (e): e is Extract<AgentEvent, { type: 'awaiting_user' }> =>
            e.type === 'awaiting_user' &&
            (e.question.toLowerCase().includes('confirm') ||
              e.question.includes('کنفرم') ||
              e.question.toLowerCase().includes('book karne lage') ||
              e.question.toLowerCase().includes('about to book') ||
              e.question.toLowerCase().includes('would you like me to confirm')),
        );
        if (confirmRequestEvent) {
          const latestRec = agentEventsRef.current
            .slice()
            .reverse()
            .find((e): e is RecommendationEvent => e.type === 'recommendation');
          if (latestRec) {
            setPendingConfirmation(latestRec);
          }
        }
      } catch (e) {
        console.error('Agent error:', e);
      } finally {
        setIsProcessing(false);
      }
    },
    [inputText, isProcessing, isConfirming, pendingConfirmation, defaultLocation, addAgentMessage, addBooking, scrollToBottom],
  );

  // ── Human-in-the-Loop Confirmation Step ─────────────────────────────────
  const handleRequestConfirmation = useCallback(
    (rec: RecommendationEvent) => {
      if (isProcessing || isConfirming) return;
      Haptics.selectionAsync();
      setPendingConfirmation(rec);

      const confirmQuestionMsg: ChatMessage = {
        id: `agent_${Date.now()}`,
        role: 'agent',
        event: {
          type: 'awaiting_user',
          question: `You're about to book ${rec.provider.name} for ${CATEGORY_LABEL[rec.provider.category] ?? rec.provider.category} (${rec.dayLabel}, ${rec.suggestedSlot}). Would you like me to confirm this booking?`,
          missing: 'service',
        },
        timestamp: formatCurrentTime(),
      };
      setMessages((prev) => [...prev, confirmQuestionMsg]);
      scrollToBottom();
    },
    [isProcessing, isConfirming, scrollToBottom],
  );

  const handleCancelConfirmation = useCallback(() => {
    if (isConfirming) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const cancelledProvider = pendingConfirmation?.provider;
    setPendingConfirmation(null);

    const cancelMsg: ChatMessage = {
      id: `agent_${Date.now()}`,
      role: 'agent',
      event: {
        type: 'awaiting_user',
        question: cancelledProvider
          ? `Booking not confirmed. ${cancelledProvider.name} is still available above, or you can request a different time or provider.`
          : `Booking cancelled. Feel free to request another service or time whenever you're ready.`,
        missing: 'service',
      },
      timestamp: formatCurrentTime(),
    };
    setMessages((prev) => [...prev, cancelMsg]);
    scrollToBottom();
  }, [pendingConfirmation, isConfirming, scrollToBottom]);

  const handleConfirmBooking = useCallback(
    async (rec: RecommendationEvent) => {
      if (isConfirming || isProcessing) return;
      setIsConfirming(true);
      setIsProcessing(true);
      setPendingConfirmation(null);

      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

      const bookingFlowEvents: AgentEvent[] = [];

      try {
        const gen = confirmBooking(rec.provider, rec.suggestedSlot, rec.dayLabel);

        for await (const event of gen) {
          addAgentMessage(event);
          bookingFlowEvents.push(event);
        }

        const confirmedEvent = bookingFlowEvents.find(
          (e): e is Extract<AgentEvent, { type: 'confirmed' }> =>
            e.type === 'confirmed',
        );
        const reminderEvent = bookingFlowEvents.find(
          (e): e is Extract<AgentEvent, { type: 'reminder_scheduled' }> =>
            e.type === 'reminder_scheduled',
        );

        if (confirmedEvent) {
          addBooking({
            id: confirmedEvent.bookingId,
            providerId: rec.provider.id,
            providerName: rec.provider.name,
            category: rec.provider.category,
            sector: rec.provider.sector,
            scheduledFor: `${rec.dayLabel}, ${rec.suggestedSlot}`,
            scheduledTimestamp: rec.scheduledTimestamp,
            status: 'confirmed',
            reminderAt: reminderEvent?.at ?? '1 hour before',
            agentThread: [...agentEventsRef.current],
            createdAt: Date.now(),
          });
        }
      } catch (e) {
        console.error('Booking error:', e);
        Alert.alert('Booking Error', 'Could not confirm the booking. Please try again.');
      } finally {
        setIsConfirming(false);
        setIsProcessing(false);
      }
    },
    [isConfirming, isProcessing, addAgentMessage, addBooking],
  );

  const handleChipPress = useCallback(
    (promptText: string) => {
      handleSend(promptText);
    },
    [handleSend],
  );

  const handleNewChat = useCallback(() => {
    if (messages.length === 0 || isProcessing || isConfirming) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert(
      'Start a new chat?',
      'This clears the current conversation and resets the assistant.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'New Chat',
          style: 'destructive',
          onPress: () => {
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            resetConversationSession();
            setPendingConfirmation(null);
            setIsConfirming(false);
            setMessages([]);
            setAgentEvents([]);
            agentEventsRef.current = [];
            setInputText('');
          },
        },
      ],
    );
  }, [messages.length, isProcessing, isConfirming]);

  const handleGpsBadgePress = useCallback(async () => {
    Haptics.selectionAsync();
    await requestLocationPermission();
  }, [requestLocationPermission]);

  // Contextual smart quick-suggestions based on current state
  const lastEvent = agentEvents[agentEvents.length - 1];
  const lastRecEvent = agentEvents.find(
    (e): e is RecommendationEvent => e.type === 'recommendation',
  );
  const isConfirmed = agentEvents.some((e) => e.type === 'confirmed');

  const getContextualSuggestions = (): string[] => {
    if (isProcessing || isConfirming || isConfirmed) return [];

    if (pendingConfirmation) {
      return ['✅ Confirm Booking', '❌ Cancel'];
    }

    if (lastEvent?.type === 'awaiting_user') {
      const q = lastEvent.question.toLowerCase();
      if (
        q.includes('confirm') ||
        q.includes('book karne lage') ||
        q.includes('would you like me to confirm')
      ) {
        return ['✅ Confirm Booking', '❌ Cancel'];
      }
      if (lastEvent.missing === 'location') {
        return hasGps
          ? ['📍 Use My GPS Location', 'G-13 Islamabad', 'F-10 Markaz', 'I-8 Rawalpindi']
          : ['G-13 Islamabad', 'F-10 Markaz', 'I-8 Rawalpindi', 'DHA Phase 2'];
      }
      if (lastEvent.missing === 'time') {
        return ['⏰ Abhi chahiye (ASAP)', 'Kal subah 10 baje', 'Aaj sham 5 baje', 'Sunday morning'];
      }
      if (lastEvent.missing === 'service') {
        return ['❄️ AC Technician', '🔧 Plumber', '⚡ Electrician', '🧹 Home Cleaner'];
      }
    }

    if (lastEvent?.type === 'recommendation') {
      return ['📅 Book Appointment', '🔄 Show another provider', 'Visiting charges kya hain?'];
    }

    return [];
  };

  const contextualSuggestions = getContextualSuggestions();

  // ── Render a single agent event as bubble content ──────────

  const renderAgentEvent = useCallback(
    (event: AgentEvent, isLast: boolean, timestamp: string) => {
      const showLoading = isLast && isProcessing;
      switch (event.type) {
        case 'understanding':
          // Internal booking state is retained internally and not rendered as status cards in the chat UI
          return null;

        case 'searching':
          // Search progress messages removed from user chat per Change 1
          return null;

        case 'ranking':
          // Ranking progress messages removed from user chat per Change 1
          return null;

        case 'recommendation':
          return (
            <ChatBubble side="agent" fullWidth timestamp={timestamp}>
              <Text className="mb-1 text-[15px] font-medium text-gray-900">
                Here&apos;s the best matched provider based on distance, reviews, rating, and availability:
              </Text>
              <ProviderCard
                provider={event.provider}
                distanceKm={event.distanceKm}
                reasoning={event.reasoning}
                suggestedSlot={event.suggestedSlot}
                dayLabel={event.dayLabel}
                onBook={() => handleRequestConfirmation(event)}
              />
            </ChatBubble>
          );

        case 'awaiting_user':
          return (
            <ChatBubble side="agent" timestamp={timestamp}>
              <Text className="text-[15px] leading-5 text-gray-900">
                {event.question}
              </Text>
            </ChatBubble>
          );

        case 'booking':
          return (
            <View>
              <ChatBubble side="agent" timestamp={timestamp}>
                <Text className="text-[15px] text-gray-900">
                  Booking the slot <Text className="font-semibold">{event.slot}</Text> with{' '}
                  <Text className="font-semibold">{event.provider.name}</Text>...
                </Text>
              </ChatBubble>
              {showLoading && <TypingIndicator />}
            </View>
          );

        case 'confirmed':
          return (
            <ChatBubble side="agent" tone="success" timestamp={timestamp}>
              <View className="flex-row items-center">
                <Ionicons name="checkmark-done-circle" size={20} color="#15803D" style={{ marginRight: 8 }} />
                <View className="flex-1">
                  <Text className="text-[15px] font-bold text-green-900">
                    Booking Confirmed!
                  </Text>
                  <Text className="mt-0.5 text-xs text-green-800">
                    Your appointment has been secured with the provider.
                  </Text>
                </View>
              </View>
            </ChatBubble>
          );

        case 'reminder_scheduled':
          return (
            <ChatBubble side="agent" timestamp={timestamp}>
              <View className="flex-row items-center">
                <Ionicons name="notifications-outline" size={16} color="#4B5563" style={{ marginRight: 6 }} />
                <Text className="text-[14px] text-gray-900 flex-1">
                  Reminder set for <Text className="font-semibold">{event.at}</Text> (1 hour prior to visit).
                </Text>
              </View>
            </ChatBubble>
          );

        case 'rescheduled':
          return (
            <ChatBubble side="agent" tone="success" timestamp={timestamp}>
              <View className="flex-row items-center mb-1">
                <Ionicons name="calendar-outline" size={18} color="#047857" style={{ marginRight: 6 }} />
                <Text className="text-[15px] font-bold text-emerald-900 flex-1">
                  Appointment Rescheduled
                </Text>
              </View>
              <Text className="text-[14px] leading-5 text-gray-800">
                {event.message}
              </Text>
              <View className="mt-2 self-start rounded-full bg-emerald-100 px-3 py-1 flex-row items-center">
                <Ionicons name="time-outline" size={14} color="#065f46" style={{ marginRight: 4 }} />
                <Text className="text-xs font-semibold text-emerald-800">
                  New Time: {event.newSlot}
                </Text>
              </View>
            </ChatBubble>
          );

        default:
          return null;
      }
    },
    [handleRequestConfirmation, isProcessing],
  );

  const showEmptyState = messages.length === 0;

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 60 + insets.bottom : 20}
      >
        {/* App Header */}
        <View className="flex-row items-center justify-between border-b border-gray-100 bg-white px-5 pb-3 pt-2">
          <View className="flex-row items-center">
            <View className="h-9 w-9 items-center justify-center rounded-full bg-primary-100/90 border border-primary-200/60 mr-2.5">
              <Ionicons name="flash" size={17} color="#F97316" />
            </View>
            <View>
              <View className="flex-row items-center">
                <Text className="text-lg font-bold text-gray-900">Khidmat</Text>
                <View className="ml-2 flex-row items-center rounded-full bg-green-50 px-2 py-0.5 border border-green-200/60">
                  <View className="h-1.5 w-1.5 rounded-full bg-green-500" />
                  <Text className="ml-1 text-[10px] font-semibold text-green-700">Online</Text>
                </View>
              </View>
              <Text className="text-xs text-gray-400">
                AI Service Assistant
              </Text>
            </View>
          </View>

          <View className="flex-row items-center gap-2">
            {/* GPS location status badge */}
            <Pressable
              onPress={handleGpsBadgePress}
              className={`flex-row items-center gap-1 rounded-full px-2.5 py-1 border ${
                isFetching
                  ? 'bg-yellow-50 border-yellow-200'
                  : hasGps
                    ? 'bg-green-50 border-green-200'
                    : 'bg-gray-100 border-gray-200'
              }`}
            >
              <Ionicons
                name={
                  isFetching
                    ? 'locate'
                    : hasGps
                      ? 'location'
                      : 'location-outline'
                }
                size={12}
                color={isFetching ? '#d97706' : hasGps ? '#16a34a' : '#9ca3af'}
              />
              <Text
                className={`text-[10px] font-semibold ${
                  isFetching
                    ? 'text-yellow-700'
                    : hasGps
                      ? 'text-green-700'
                      : 'text-gray-500'
                }`}
              >
                {isFetching ? 'Locating…' : hasGps ? 'GPS Active' : 'Enable GPS'}
              </Text>
            </Pressable>

            {messages.length > 0 && !isProcessing && (
              <Pressable
                onPress={handleNewChat}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                className="h-9 w-9 items-center justify-center rounded-full bg-gray-100 active:bg-gray-200"
              >
                <Ionicons name="create-outline" size={18} color="#4B5563" />
              </Pressable>
            )}
          </View>
        </View>

        {/* Chat message stream */}
        <ScrollView
          ref={scrollRef}
          className="flex-1 px-4 pt-3"
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
          showsVerticalScrollIndicator={false}
          onContentSizeChange={() => {
            if (!showEmptyState) {
              scrollToBottom(50);
            }
          }}
          contentContainerStyle={
            showEmptyState ? { flexGrow: 1 } : { paddingBottom: 16 }
          }
        >
          {showEmptyState ? (
            <View className="flex-1 justify-center px-1 pb-6">
              {/* Greeting Card */}
              <View className="rounded-3xl border border-gray-100 bg-white p-5">
                <Text className="text-2xl font-extrabold text-gray-900">
                  Assalam-o-Alaikum 👋
                </Text>
                <Text className="mt-1 text-base font-semibold text-gray-700">
                  What service can we help you with today?
                </Text>
                <Text className="mt-1 text-xs text-gray-400">
                  Ask freely in Urdu, Roman Urdu, or English.
                </Text>

                {/* Service Category Quick Pills */}
                <View className="mt-4 flex-row flex-wrap gap-2">
                  {SERVICE_SHORTCUTS.map((item) => (
                    <Pressable
                      key={item.label}
                      onPress={() => handleChipPress(item.prompt)}
                      className="flex-row items-center rounded-xl border border-gray-200/80 bg-gray-50/80 px-3 py-2 active:bg-primary-50 active:border-primary-300"
                    >
                      <Text className="mr-1.5 text-sm">{item.icon}</Text>
                      <Text className="text-xs font-semibold text-gray-800">
                        {item.label}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>

              {/* Popular prompt chips */}
              <View className="mt-5">
                <Text className="mb-2.5 px-1 text-xs font-bold uppercase tracking-wider text-gray-400">
                  Popular Requests
                </Text>
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <ExamplePromptChip
                    key={prompt.text}
                    text={prompt.text}
                    icon={prompt.icon}
                    onPress={() => handleChipPress(prompt.text)}
                  />
                ))}
              </View>
            </View>
          ) : (
            <>
              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1;
                if (msg.role === 'user') {
                  return (
                    <FadeInSlide key={msg.id}>
                      <ChatBubble side="user" timestamp={msg.timestamp}>
                        {msg.text}
                      </ChatBubble>
                    </FadeInSlide>
                  );
                }
                const content = renderAgentEvent(msg.event, isLast, msg.timestamp);
                if (!content) return null;
                return (
                  <FadeInSlide key={msg.id}>
                    {content}
                  </FadeInSlide>
                );
              })}

              {/* Human-in-the-Loop Booking Confirmation Card */}
              {pendingConfirmation && (
                <FadeInSlide>
                  <View className="my-2.5 overflow-hidden rounded-2xl border border-amber-200 bg-amber-50/70 p-3.5 shadow-sm">
                    <View className="flex-row items-start">
                      <View className="h-9 w-9 items-center justify-center rounded-xl bg-amber-100 border border-amber-200/80 mr-2.5 flex-shrink-0">
                        <Ionicons name="help-circle" size={18} color="#D97706" />
                      </View>
                      <View className="flex-1 min-w-0">
                        <Text className="text-[14px] font-bold text-gray-900" numberOfLines={1}>
                          Confirm Your Appointment
                        </Text>
                        <Text className="mt-1 text-[13px] leading-5 text-gray-700">
                          You&apos;re about to book{' '}
                          <Text className="font-semibold text-gray-900">{pendingConfirmation.provider.name}</Text>{' '}
                          for{' '}
                          <Text className="font-semibold text-gray-900">
                            {CATEGORY_LABEL[pendingConfirmation.provider.category] ?? pendingConfirmation.provider.category}
                          </Text>{' '}
                          ({pendingConfirmation.dayLabel && pendingConfirmation.dayLabel !== 'Scheduled' && !pendingConfirmation.suggestedSlot.toLowerCase().includes(pendingConfirmation.dayLabel.toLowerCase())
                            ? `${pendingConfirmation.dayLabel}, `
                            : ''}
                          {pendingConfirmation.suggestedSlot}).
                        </Text>
                        <Text className="mt-1 text-[13px] font-semibold text-amber-950">
                          Would you like me to confirm this booking?
                        </Text>
                      </View>
                    </View>

                    <View className="mt-3 flex-row items-center gap-2">
                      <Pressable
                        disabled={isConfirming || isProcessing}
                        onPress={handleCancelConfirmation}
                        className="flex-1 items-center justify-center rounded-xl border border-gray-300 bg-white py-2.5 px-2 active:bg-gray-100"
                      >
                        <Text className="text-xs font-bold text-gray-700 text-center" numberOfLines={1}>
                          Cancel
                        </Text>
                      </Pressable>

                      <Pressable
                        disabled={isConfirming || isProcessing}
                        onPress={() => handleConfirmBooking(pendingConfirmation)}
                        className={`flex-1 flex-row items-center justify-center rounded-xl py-2.5 px-2 ${
                          isConfirming ? 'bg-primary-400' : 'bg-primary active:bg-primary-600'
                        } shadow-sm`}
                      >
                        {isConfirming ? (
                          <DotsLoader />
                        ) : (
                          <>
                            <Ionicons
                              name="checkmark-circle-outline"
                              size={15}
                              color="#FFFFFF"
                              style={{ marginRight: 4 }}
                            />
                            <Text className="text-xs font-bold text-white text-center" numberOfLines={1}>
                              Confirm Booking
                            </Text>
                          </>
                        )}
                      </Pressable>
                    </View>
                  </View>
                </FadeInSlide>
              )}


            </>
          )}
        </ScrollView>

        {/* Contextual Smart Suggestion Chips */}
        {contextualSuggestions.length > 0 && (
          <View className="border-t border-gray-100 bg-white px-3 pt-2 pb-1">
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ gap: 8, paddingHorizontal: 2 }}
            >
              {contextualSuggestions.map((suggestion, idx) => (
                <Pressable
                  key={idx}
                  disabled={isConfirming || isProcessing}
                  onPress={() => {
                    Haptics.selectionAsync();
                    if (suggestion === '📍 Use My GPS Location') {
                      if (coordinates) {
                        handleSend(`Meri location yeh hai: ${coordinates.latitude}, ${coordinates.longitude}`);
                      } else {
                        handleGpsBadgePress();
                      }
                    } else if (suggestion === '✅ Confirm Booking') {
                      const target = pendingConfirmation || lastRecEvent;
                      if (target) {
                        handleConfirmBooking(target);
                      } else {
                        handleSend('Confirm booking');
                      }
                    } else if (suggestion === '❌ Cancel') {
                      handleCancelConfirmation();
                    } else if (suggestion === '📅 Book Appointment' && lastRecEvent) {
                      handleRequestConfirmation(lastRecEvent);
                    } else {
                      handleSend(suggestion);
                    }
                  }}
                  className="rounded-full border border-primary-200 bg-primary-50 px-3.5 py-1.5 active:bg-primary-100 active:opacity-80"
                >
                  <Text className="text-xs font-semibold text-primary-900">
                    {suggestion}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>
          </View>
        )}

        {/* Input Bar */}
        <InputBar
          value={inputText}
          onChangeText={setInputText}
          onSend={() => handleSend()}
          placeholder="Type in English, Urdu, or Roman Urdu..."
          disabled={isProcessing || isConfirming}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

