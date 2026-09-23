import React from 'react';
import { View, Text } from 'react-native';

type StatusBadgeProps = {
  status: 'confirmed' | 'reminded' | 'completed' | 'cancelled';
};

const STATUS_STYLES: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  confirmed: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Confirmed' },
  reminded: {
    bg: 'bg-primary-100',
    text: 'text-primary-700',
    label: 'Reminded',
  },
  completed: {
    bg: 'bg-green-100',
    text: 'text-green-700',
    label: 'Completed',
  },
  cancelled: {
    bg: 'bg-gray-100',
    text: 'text-gray-500',
    label: 'Cancelled',
  },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.confirmed;

  return (
    <View className={`rounded-full px-3 py-1 ${style.bg}`}>
      <Text className={`text-xs font-semibold ${style.text}`}>
        {style.label}
      </Text>
    </View>
  );
}
