import React from 'react';
import { Pressable, Text } from 'react-native';

type ExamplePromptChipProps = {
  text: string;
  onPress: () => void;
};

export function ExamplePromptChip({ text, onPress }: ExamplePromptChipProps) {
  return (
    <Pressable
      onPress={onPress}
      className="mb-2 rounded-2xl border border-primary-200 bg-primary-50 px-4 py-2.5 active:bg-primary-100"
    >
      <Text className="text-[13px] leading-5 text-primary-800">{text}</Text>
    </Pressable>
  );
}
