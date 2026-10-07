import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type ChatBubbleProps = {
  side: 'user' | 'agent';
  tone?: 'default' | 'success';
  timestamp?: string;
  showAvatar?: boolean;
  children: React.ReactNode;
};

export function ChatBubble({
  side,
  tone = 'default',
  timestamp,
  showAvatar = true,
  children,
}: ChatBubbleProps) {
  const isUser = side === 'user';

  // KEEP EXACT EXISTING COLORS:
  // User query box: bg-primary (Khidmat Orange) with text-white
  // Agent response box: bg-gray-100 with text-gray-900 (or bg-green-50 with text-green-900 for success)
  const bubbleBg = isUser
    ? 'bg-primary'
    : tone === 'success'
      ? 'bg-green-50 border border-green-200/60'
      : 'bg-gray-100';

  const textColor = isUser
    ? 'text-white'
    : tone === 'success'
      ? 'text-green-900'
      : 'text-gray-900';

  return (
    <View className={`mb-3 ${isUser ? 'items-end' : 'items-start'}`}>
      <View className="flex-row items-end max-w-[88%]">
        {/* Agent Avatar Icon */}
        {!isUser && showAvatar && (
          <View className="mr-2 mb-1 h-7 w-7 items-center justify-center rounded-full bg-primary/10 border border-primary/20 shadow-xs">
            <Ionicons name="sparkles" size={14} color="#F97316" />
          </View>
        )}

        {/* Chat Bubble Container */}
        <View
          className={`flex-1 px-4 py-3 shadow-xs ${bubbleBg} ${
            isUser
              ? 'rounded-2xl rounded-br-xs'
              : 'rounded-2xl rounded-bl-xs'
          }`}
        >
          {typeof children === 'string' ? (
            <Text className={`text-[15px] leading-[22px] font-normal ${textColor}`}>
              {children}
            </Text>
          ) : (
            <View>{children}</View>
          )}

          {/* Timestamp and delivery receipt */}
          {timestamp && (
            <View
              className={`mt-1.5 flex-row items-center ${
                isUser ? 'justify-end' : 'justify-start'
              }`}
            >
              <Text
                className={`text-[10px] tracking-tight ${
                  isUser ? 'text-white/75' : 'text-gray-400'
                }`}
              >
                {timestamp}
              </Text>
              {isUser && (
                <Ionicons
                  name="checkmark-done"
                  size={12}
                  color="rgba(255, 255, 255, 0.85)"
                  style={{ marginLeft: 3 }}
                />
              )}
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

