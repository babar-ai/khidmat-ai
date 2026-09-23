import React from 'react';
import { Pressable, Text } from 'react-native';

type ButtonProps = {
  variant?: 'primary' | 'secondary' | 'destructive';
  onPress: () => void;
  children: React.ReactNode;
  disabled?: boolean;
};

export function Button({
  variant = 'primary',
  onPress,
  children,
  disabled = false,
}: ButtonProps) {
  const base = 'items-center justify-center rounded-xl py-3 px-6';

  const variantStyles = {
    primary: 'bg-primary active:bg-primary-600',
    secondary: 'bg-gray-100 active:bg-gray-200',
    destructive: 'border border-red-300 bg-white active:bg-red-50',
  };

  const textStyles = {
    primary: 'text-white font-bold text-sm',
    secondary: 'text-gray-900 font-semibold text-sm',
    destructive: 'text-red-600 font-semibold text-sm',
  };

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      className={`${base} ${variantStyles[variant]} ${disabled ? 'opacity-50' : ''}`}
    >
      <Text className={textStyles[variant]}>
        {typeof children === 'string' ? children : children}
      </Text>
    </Pressable>
  );
}
