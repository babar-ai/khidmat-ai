import React from 'react';
import { View, Text } from 'react-native';

type ChatBubbleProps = {
  side: 'user' | 'agent';
  tone?: 'default' | 'success';
  children: React.ReactNode;
};

export function ChatBubble({
  side,
  tone = 'default',
  children,
}: ChatBubbleProps) {
  const isUser = side === 'user';

  const containerAlign = isUser ? 'items-end' : 'items-start';

  const bubbleBg = isUser
    ? 'bg-primary'
    : tone === 'success'
      ? 'bg-green-50'
      : 'bg-gray-100';

  const textColor = isUser
    ? 'text-white'
    : tone === 'success'
      ? 'text-green-900'
      : 'text-gray-900';

  return (
    <View className={`mb-2 ${containerAlign}`}>
      <View
        className={`max-w-[85%] px-4 py-3 ${bubbleBg} ${
          isUser
            ? 'rounded-2xl rounded-br-md'
            : 'rounded-2xl rounded-bl-md'
        }`}
      >
        {typeof children === 'string' ? (
          <Text className={`text-[15px] leading-5 ${textColor}`}>
            {children}
          </Text>
        ) : (
          <View>{children}</View>
        )}
      </View>
    </View>
  );
}
