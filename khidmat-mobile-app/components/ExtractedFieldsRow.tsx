import React from 'react';
import { View, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type ExtractedFieldsRowProps = {
  service: string | null;
  location: string | null;
  time: string | null;
};

export function ExtractedFieldsRow({
  service,
  location,
  time,
}: ExtractedFieldsRowProps) {
  const fields = [
    {
      icon: 'construct-outline' as const,
      label: service ?? 'Pending',
      filled: Boolean(service),
      badgeStyle: service
        ? 'bg-orange-100/80 border-orange-200 text-orange-900'
        : 'bg-gray-200/60 border-gray-300/50 text-gray-500',
      iconColor: service ? '#EA580C' : '#9CA3AF',
    },
    {
      icon: 'location-outline' as const,
      label: location ?? 'Pending',
      filled: Boolean(location),
      badgeStyle: location
        ? 'bg-blue-100/80 border-blue-200 text-blue-900'
        : 'bg-gray-200/60 border-gray-300/50 text-gray-500',
      iconColor: location ? '#2563EB' : '#9CA3AF',
    },
    {
      icon: 'time-outline' as const,
      label: time ?? 'Pending',
      filled: Boolean(time),
      badgeStyle: time
        ? 'bg-purple-100/80 border-purple-200 text-purple-900'
        : 'bg-gray-200/60 border-gray-300/50 text-gray-500',
      iconColor: time ? '#9333EA' : '#9CA3AF',
    },
  ];

  return (
    <View className="mt-2.5 flex-row flex-wrap gap-2">
      {fields.map((field, idx) => (
        <View
          key={idx}
          className={`flex-row items-center rounded-xl border px-2.5 py-1.5 ${field.badgeStyle.split(' ')[0]} ${field.badgeStyle.split(' ')[1]}`}
        >
          <Ionicons name={field.icon} size={13} color={field.iconColor} />
          <Text
            className={`ml-1.5 text-xs font-semibold capitalize ${field.badgeStyle.split(' ')[2]}`}
          >
            {field.label}
          </Text>
        </View>
      ))}
    </View>
  );
}

