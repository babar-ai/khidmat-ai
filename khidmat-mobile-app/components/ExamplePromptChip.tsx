import React from 'react';
import { Pressable, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

type ExamplePromptChipProps = {
  text: string;
  icon?: string;
  onPress: () => void;
};

export function ExamplePromptChip({ text, icon, onPress }: ExamplePromptChipProps) {
  const handlePress = () => {
    Haptics.selectionAsync();
    onPress();
  };

  return (
    <Pressable
      onPress={handlePress}
      className="mb-2.5 flex-row items-center justify-between rounded-2xl border border-primary-200/80 bg-primary-50/70 px-4 py-3 active:bg-primary-100/90 active:opacity-80"
    >
      <View className="flex-1 flex-row items-center pr-2">
        {icon ? (
          <Text className="mr-2.5 text-base">{icon}</Text>
        ) : (
          <Ionicons
            name="chatbubble-ellipses-outline"
            size={16}
            color="#EA580C"
            style={{ marginRight: 8 }}
          />
        )}
        <Text className="flex-1 text-[14px] font-medium leading-5 text-primary-950">
          {text}
        </Text>
      </View>
      <Ionicons name="arrow-forward" size={14} color="#EA580C" />
    </Pressable>
  );
}

