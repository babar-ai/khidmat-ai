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
import { runAgent, confirmBooking } from '@/lib/agent/mockAgent';
import { useSettingsStore } from '@/lib/stores/useSettingsStore';
import { useBookingsStore } from '@/lib/stores/useBookingsStore';
import type { AgentEvent } from '@/lib/agent/types';

type RecommendationEvent = Extract<AgentEvent, { type: 'recommendation' }>;

// ── Types for chat messages ─────────────────────────────────────

type ChatMessage =
  | { id: string; role: 'user'; text: string }
  | { id: string; role: 'agent'; event: AgentEvent };

// ── Animated wrapper for fade-in ────────────────────────────────

function FadeIn({ children }: { children: React.ReactNode }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(opacity, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [opacity]);

  return <Animated.View style={{ opacity }}>{children}</Animated.View>;
}

// ── Dots loader ─────────────────────────────────────────────────

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
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(dot, {
            toValue: 0,
            duration: 300,
            useNativeDriver: true,
          }),
        ]),
      ).start();
    };
    animate(dot1, 0);
    animate(dot2, 200);
    animate(dot3, 400);
  }, [dot1, dot2, dot3]);

  return (
    <View className="flex-row items-center gap-1">
      {[dot1, dot2, dot3].map((dot, i) => (
        <Animated.View
          key={i}
          style={{ opacity: dot }}
          className="h-1.5 w-1.5 rounded-full bg-gray-400"
        />
      ))}
    </View>
  );
}

// ── Typing indicator (separate small bubble) ────────────────────

function TypingIndicator() {
  return (
    <View className="mb-2 items-start">
      <View className="rounded-2xl rounded-bl-md bg-gray-100 px-4 py-2.5">
        <DotsLoader />
      </View>
    </View>
  );
}

// ── Example prompts ─────────────────────────────────────────────

const EXAMPLE_PROMPTS = [
  'Mujhe kal subah G-13 mein AC technician chahiye',
  'Plumber abhi chahiye, bathroom mein leak hai',
  'Math tutor for my son, F-10',
  'Beautician chahiye Sunday ko, home service',
];

// ── Category display names ──────────────────────────────────────

const CATEGORY_LABEL: Record<string, string> = {
  ac: 'AC Technician',
  plumber: 'Plumber',
  electrician: 'Electrician',
  tutor: 'Tutor',
  beautician: 'Beautician',
};

// ── Main Chat Screen ────────────────────────────────────────────

export default function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([]);
  const scrollRef = useRef<ScrollView>(null);
  // Ref to always have the latest events (avoids stale closures)
  const agentEventsRef = useRef<AgentEvent[]>([]);

  const insets = useSafeAreaInsets();
  const defaultLocation = useSettingsStore((s) => s.defaultLocation);
  const addBooking = useBookingsStore((s) => s.addBooking);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 100);
  }, []);

  const addAgentMessage = useCallback(
    (event: AgentEvent) => {
      const msg: ChatMessage = {
        id: `agent_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        role: 'agent',
        event,
      };
      setMessages((prev) => [...prev, msg]);
      setAgentEvents((prev) => {
        const next = [...prev, event];
        agentEventsRef.current = next;
        return next;
      });
      if (event.type === 'confirmed') {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
      scrollToBottom();
    },
    [scrollToBottom],
  );

  const handleSend = useCallback(async () => {
    const text = inputText.trim();
    if (!text || isProcessing) return;

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setInputText('');
    setIsProcessing(true);

    // Add user message
    const userMsg: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      text,
    };
    setMessages((prev) => [...prev, userMsg]);
    scrollToBottom();

    // Run agent
    try {
      const gen = runAgent(text, {
        defaultLocation,
        conversationHistory: agentEventsRef.current,
      });

      for await (const event of gen) {
        addAgentMessage(event);
      }
    } catch (e) {
      console.error('Agent error:', e);
    } finally {
      setIsProcessing(false);
    }
  }, [inputText, isProcessing, defaultLocation, addAgentMessage, scrollToBottom]);

  const handleBook = useCallback(
    async (rec: RecommendationEvent) => {
      if (isProcessing) return;
      setIsProcessing(true);

      // Collect booking-flow events locally so we don't depend on stale state
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
      } finally {
        setIsProcessing(false);
      }
    },
    [isProcessing, addAgentMessage, addBooking],
  );

  const handleChipPress = useCallback(
    (text: string) => {
      setInputText(text);
    },
    [],
  );

  const handleNewChat = useCallback(() => {
    if (messages.length === 0 || isProcessing) return;
    Alert.alert(
      'Start a new chat?',
      'This clears the current conversation.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'New Chat',
          onPress: () => {
            setMessages([]);
            setAgentEvents([]);
            agentEventsRef.current = [];
            setInputText('');
          },
        },
      ],
    );
  }, [messages.length, isProcessing]);

  // ── Render a single agent event as bubble content ──────────

  const renderAgentEvent = useCallback(
    (event: AgentEvent, isLast: boolean) => {
      const showLoading = isLast && isProcessing;
      switch (event.type) {
        case 'understanding': {
          const { extracted, usedDefaultLocation } = event;
          const locationLabel = usedDefaultLocation
            ? `${extracted.location} (your home)`
            : extracted.location;
          return (
            <ChatBubble side="agent">
              <Text className="text-[15px] leading-5 text-gray-900">
                Got it, here&apos;s what I understood:
              </Text>
              <ExtractedFieldsRow
                service={
                  extracted.service
                    ? CATEGORY_LABEL[extracted.service] ?? extracted.service
                    : null
                }
                location={locationLabel}
                time={extracted.time}
              />
            </ChatBubble>
          );
        }

        case 'searching':
          return (
            <View>
              <ChatBubble side="agent">
                <Text className="text-[15px] text-gray-900">
                  Looking for {CATEGORY_LABEL[event.category] ?? event.category}{' '}
                  near {event.near}
                </Text>
              </ChatBubble>
              {showLoading && <TypingIndicator />}
            </View>
          );

        case 'ranking':
          return (
            <View>
              <ChatBubble side="agent">
                <Text className="text-[15px] text-gray-900">
                  Found {event.candidateCount} nearby. Ranking by distance,
                  rating, and availability
                </Text>
              </ChatBubble>
              {showLoading && <TypingIndicator />}
            </View>
          );

        case 'recommendation':
          return (
            <ChatBubble side="agent">
              <Text className="mb-1 text-[15px] text-gray-900">
                Here&apos;s who I&apos;d recommend:
              </Text>
              <ProviderCard
                provider={event.provider}
                distanceKm={event.distanceKm}
                reasoning={event.reasoning}
                suggestedSlot={event.suggestedSlot}
                dayLabel={event.dayLabel}
                onBook={() => handleBook(event)}
              />
            </ChatBubble>
          );

        case 'awaiting_user':
          return (
            <ChatBubble side="agent">
              <Text className="text-[15px] text-gray-900">
                {event.question}
              </Text>
            </ChatBubble>
          );

        case 'booking':
          return (
            <View>
              <ChatBubble side="agent">
                <Text className="text-[15px] text-gray-900">
                  Booking the {event.slot} slot with {event.provider.name}
                </Text>
              </ChatBubble>
              {showLoading && <TypingIndicator />}
            </View>
          );

        case 'confirmed':
          return (
            <ChatBubble side="agent" tone="success">
              <Text className="text-[15px] font-semibold text-green-900">
                ✅ Confirmed! Your booking is set.
              </Text>
            </ChatBubble>
          );

        case 'reminder_scheduled':
          return (
            <ChatBubble side="agent">
              <Text className="text-[15px] text-gray-900">
                ⏰ I&apos;ll remind you at {event.at} — 1 hour before your
                appointment.
              </Text>
            </ChatBubble>
          );

        default:
          return null;
      }
    },
    [handleBook, isProcessing],
  );

  // ── Empty state ────────────────────────────────────────────

  const showEmptyState = messages.length === 0;

  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      <KeyboardAvoidingView
        className="flex-1"
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={60 + insets.bottom}
      >
        {/* Header */}
        <View className="flex-row items-center justify-between border-b border-gray-50 px-5 pb-3 pt-2">
          <View>
            <Text className="text-lg font-bold text-gray-900">Khidmat</Text>
            <Text className="text-xs text-gray-400">
              Your AI service assistant
            </Text>
          </View>
          {messages.length > 0 && !isProcessing && (
            <Pressable
              onPress={handleNewChat}
              className="h-9 w-9 items-center justify-center rounded-full bg-gray-50 active:bg-gray-100"
            >
              <Ionicons name="create-outline" size={18} color="#6b7280" />
            </Pressable>
          )}
        </View>

        {/* Chat messages */}
        <ScrollView
          ref={scrollRef}
          className="flex-1 px-4 pt-4"
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          contentContainerStyle={
            showEmptyState ? { flexGrow: 1 } : { paddingBottom: 16 }
          }
        >
          {showEmptyState ? (
            <View className="flex-1 justify-center px-2 pb-8">
              {/* Greeting */}
              <Text className="text-3xl font-bold text-gray-900">
                Assalam-o-Alaikum 👋
              </Text>
              <Text className="mt-2 text-xl font-semibold text-gray-700">
                What service do you need?
              </Text>
              <Text className="mt-1 text-sm text-gray-400">
                Type in English, Urdu, or Roman Urdu
              </Text>

              {/* Example chips */}
              <View className="mt-6">
                {EXAMPLE_PROMPTS.map((prompt) => (
                  <ExamplePromptChip
                    key={prompt}
                    text={prompt}
                    onPress={() => handleChipPress(prompt)}
                  />
                ))}
              </View>
            </View>
          ) : (
            <>
              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1;
                return (
                  <FadeIn key={msg.id}>
                    {msg.role === 'user' ? (
                      <ChatBubble side="user">{msg.text}</ChatBubble>
                    ) : (
                      renderAgentEvent(msg.event, isLast)
                    )}
                  </FadeIn>
                );
              })}

              {/* Footer link after booking confirmed */}
              {agentEvents.some((e) => e.type === 'confirmed') && (
                <FadeIn>
                  <Text
                    className="mt-2 text-center text-xs text-primary"
                    onPress={() => router.push('/(tabs)/bookings')}
                  >
                    View this booking in your Bookings tab →
                  </Text>
                </FadeIn>
              )}
            </>
          )}
        </ScrollView>

        {/* Input bar */}
        <InputBar
          value={inputText}
          onChangeText={setInputText}
          onSend={handleSend}
          placeholder="Type your request..."
          disabled={isProcessing}
        />
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
