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
      icon: 'construct' as const,
      label: service ?? 'Unknown',
      color: service ? 'bg-primary-100 text-primary-800' : 'bg-gray-200 text-gray-500',
    },
    {
      icon: 'location' as const,
      label: location ?? 'Unknown',
      color: location ? 'bg-blue-100 text-blue-800' : 'bg-gray-200 text-gray-500',
    },
    {
      icon: 'time' as const,
      label: time ?? 'Unknown',
      color: time ? 'bg-purple-100 text-purple-800' : 'bg-gray-200 text-gray-500',
    },
  ];

  return (
    <View className="mt-2 flex-row flex-wrap gap-2">
      {fields.map((field) => (
        <View
          key={field.icon}
          className={`flex-row items-center rounded-full px-3 py-1.5 ${field.color.split(' ')[0]}`}
        >
          <Ionicons
            name={field.icon}
            size={13}
            color={
              field.color.includes('primary')
                ? '#9A3412'
                : field.color.includes('blue')
                  ? '#1e40af'
                  : field.color.includes('purple')
                    ? '#6b21a8'
                    : '#6b7280'
            }
          />
          <Text
            className={`ml-1.5 text-xs font-semibold capitalize ${field.color.split(' ')[1]}`}
          >
            {field.label}
          </Text>
        </View>
      ))}
    </View>
  );
}
