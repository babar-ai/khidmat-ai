import React from 'react';
import { View, TextInput, Pressable, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

type InputBarProps = {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  placeholder?: string;
  disabled?: boolean;
};

export function InputBar({
  value,
  onChangeText,
  onSend,
  placeholder = 'Type your request...',
  disabled = false,
}: InputBarProps) {
  const isEmpty = value.trim().length === 0;

  const handleClear = () => {
    Haptics.selectionAsync();
    onChangeText('');
  };

  const handleSendPress = () => {
    if (isEmpty || disabled) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onSend();
  };

  return (
    <View className="border-t border-gray-100 bg-white/95 px-3 pb-3 pt-2">
      <View className="flex-row items-end rounded-3xl border border-gray-200/90 bg-gray-50/80 px-3 py-1 shadow-xs">
        <TextInput
          className="mr-1 max-h-24 min-h-[42px] flex-1 py-2 text-[15px] leading-5 text-gray-900"
          placeholder={placeholder}
          placeholderTextColor="#9CA3AF"
          value={value}
          onChangeText={onChangeText}
          multiline
          editable={!disabled}
          textAlignVertical="center"
          returnKeyType={Platform.OS === 'ios' ? 'default' : 'send'}
        />

        {/* Quick clear button */}
        {!isEmpty && !disabled && (
          <Pressable
            onPress={handleClear}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            className="mb-2 mr-1 h-7 w-7 items-center justify-center rounded-full bg-gray-200/70 active:bg-gray-300"
          >
            <Ionicons name="close" size={14} color="#6B7280" />
          </Pressable>
        )}

        {/* Send button */}
        <Pressable
          onPress={handleSendPress}
          disabled={isEmpty || disabled}
          className={`mb-1 h-9 w-9 items-center justify-center rounded-full transition-all ${
            isEmpty || disabled
              ? 'bg-gray-200 opacity-60'
              : 'bg-primary active:scale-95 active:bg-primary-600'
          }`}
        >
          <Ionicons
            name="arrow-up"
            size={18}
            color={isEmpty || disabled ? '#9CA3AF' : '#FFFFFF'}
          />
        </Pressable>
      </View>
    </View>
  );
}

