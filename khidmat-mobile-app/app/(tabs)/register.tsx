/**
 * app/(tabs)/register.tsx — Provider Self-Registration Screen
 *
 * Like InDrive's driver signup — service providers fill this form once
 * to register their shop/services and start receiving bookings.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { registerProvider } from '@/lib/api/khidmatApi';
import type { ProviderRegisterPayload } from '@/lib/api/khidmatApi';
import { useLocationStore } from '@/lib/stores/useLocationStore';
import * as Haptics from 'expo-haptics';

// ── Service categories (must match backend enum) ──────────────────────────────
const CATEGORIES = [
  { value: 'ac_technician', label: 'AC & Refrigeration', icon: '❄️' },
  { value: 'plumber',       label: 'Plumber',            icon: '🔧' },
  { value: 'electrician',   label: 'Electrician',   icon: '⚡' },
  { value: 'carpenter',     label: 'Carpenter',     icon: '🪚' },
  { value: 'cleaner',       label: 'Cleaner',       icon: '🧹' },
  { value: 'painter',       label: 'Painter',       icon: '🎨' },
];

// ── Form field component ──────────────────────────────────────────────────────
function Field({
  label,
  required,
  hint,
  rightAction,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  rightAction?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <View className="mb-5">
      <View className="mb-1.5 flex-row items-center justify-between">
        <Text className="text-sm font-semibold text-gray-800">
          {label}
          {required && <Text className="text-red-500"> *</Text>}
        </Text>
        {rightAction}
      </View>
      {children}
      {hint && <Text className="mt-1.5 text-xs text-gray-400">{hint}</Text>}
    </View>
  );
}

// ── Text input with consistent styling ────────────────────────────────────────
function StyledInput({
  value,
  onChangeText,
  placeholder,
  keyboardType,
  autoCapitalize,
  multiline,
  numberOfLines,
  maxLength,
}: {
  value: string;
  onChangeText: (t: string) => void;
  placeholder: string;
  keyboardType?: 'default' | 'phone-pad' | 'numeric';
  autoCapitalize?: 'none' | 'words' | 'sentences' | 'characters';
  multiline?: boolean;
  numberOfLines?: number;
  maxLength?: number;
}) {
  return (
    <TextInput
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor="#9CA3AF"
      keyboardType={keyboardType ?? 'default'}
      autoCapitalize={autoCapitalize ?? 'words'}
      autoCorrect={false}
      multiline={multiline}
      numberOfLines={numberOfLines}
      maxLength={maxLength}
      className={`rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-[15px] text-gray-900 ${
        multiline ? 'min-h-[90px]' : ''
      }`}
      style={multiline ? { textAlignVertical: 'top' } : undefined}
    />
  );
}

// ── Success screen ────────────────────────────────────────────────────────────
function SuccessView({ name, onRegisterAnother }: { name: string; onRegisterAnother: () => void }) {
  return (
    <View className="flex-1 items-center justify-center px-8">
      <View className="mb-4 h-20 w-20 items-center justify-center rounded-full bg-green-100">
        <Ionicons name="checkmark-circle" size={48} color="#16a34a" />
      </View>
      <Text className="mb-2 text-center text-2xl font-bold text-gray-900">
        You're registered! 🎉
      </Text>
      <Text className="mb-1 text-center text-base text-gray-600">
        Welcome to Khidmat, <Text className="font-semibold">{name}</Text>.
      </Text>
      <Text className="mb-8 text-center text-sm text-gray-400">
        You are now active and can start receiving booking requests.
      </Text>
      <Pressable
        onPress={onRegisterAnother}
        className="rounded-xl bg-gray-100 px-6 py-3 active:bg-gray-200"
      >
        <Text className="text-sm font-semibold text-gray-700">Register another provider</Text>
      </Pressable>
    </View>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function RegisterScreen() {
  // Form fields
  const [name, setName]                   = useState('');
  const [phone, setPhone]                 = useState('');
  const [whatsapp, setWhatsapp]           = useState('');
  const [city, setCity]                   = useState('Islamabad');
  const [category, setCategory]           = useState('');
  const [locationName, setLocationName]   = useState('');
  const [gpsCoords, setGpsCoords]         = useState<{ latitude: number; longitude: number } | null>(null);
  const [description, setDescription]     = useState('');
  const [cnic, setCnic]                   = useState('');
  const [businessReg, setBusinessReg]     = useState('');

  // UI state
  const [isSubmitting, setIsSubmitting]   = useState(false);
  const [registered, setRegistered]       = useState(false);
  const [registeredName, setRegisteredName] = useState('');

  const { coordinates, requestLocationPermission, isFetching } = useLocationStore();

  const handleUseGps = async () => {
    Haptics.selectionAsync();
    let coords = coordinates;
    if (!coords) {
      await requestLocationPermission();
      coords = useLocationStore.getState().coordinates;
    }

    if (coords) {
      setGpsCoords({ latitude: coords.latitude, longitude: coords.longitude });
      setLocationName(`GPS Location (${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)})`);
    } else {
      Alert.alert('GPS Unavailable', 'Please enable location permissions in settings or enter your area name.');
    }
  };

  const handleReset = () => {
    setName(''); setPhone(''); setWhatsapp(''); setCity('Islamabad');
    setCategory(''); setLocationName(''); setGpsCoords(null); setDescription('');
    setCnic(''); setBusinessReg('');
    setRegistered(false);
    setRegisteredName('');
  };

  const handleSubmit = async () => {
    // ── Validation ─────────────────────────────────────────────────────────
    const errors: string[] = [];
    if (!name.trim())         errors.push('Shop / company name is required.');
    if (!phone.trim())        errors.push('Phone number is required.');
    if (!category)            errors.push('Please select your service category.');
    if (!locationName.trim() && !gpsCoords) errors.push('Location is required (e.g. "G-13, Islamabad" or tap GPS).');
    if (!city.trim())         errors.push('City is required.');
    if (!cnic.trim())         errors.push('CNIC is required.');
    if (cnic.trim().length < 13) errors.push('CNIC must be at least 13 characters.');

    if (errors.length > 0) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      Alert.alert('Please fix these fields', errors.join('\n'));
      return;
    }

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setIsSubmitting(true);
    try {
      const payload: ProviderRegisterPayload = {
        name:                name.trim(),
        phone:               phone.trim(),
        whatsapp_number:     whatsapp.trim() || undefined,
        city:                city.trim(),
        category,
        location_name:       locationName.trim() || undefined,
        latitude:            gpsCoords?.latitude,
        longitude:           gpsCoords?.longitude,
        description:         description.trim() || undefined,
        cnic:                cnic.trim(),
        business_reg_number: businessReg.trim() || undefined,
      };

      const result = await registerProvider(payload);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      setRegisteredName(result.name);
      setRegistered(true);
    } catch (err: unknown) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      const message = err instanceof Error ? err.message : 'Something went wrong.';
      Alert.alert('Registration Failed', message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <SafeAreaView className="flex-1 bg-white" edges={['top']}>
      {/* Header */}
      <View className="border-b border-gray-50 px-5 pb-3 pt-4">
        <Text className="text-lg font-bold text-gray-900">Provider Registration</Text>
        <Text className="text-xs text-gray-400">Register your shop or service</Text>
      </View>

      {registered ? (
        <SuccessView name={registeredName} onRegisterAnother={handleReset} />
      ) : (
        <KeyboardAvoidingView
          className="flex-1"
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          <ScrollView
            className="flex-1 px-5 pt-5"
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
            contentContainerStyle={{ paddingBottom: 40 }}
          >
            {/* ── Section: Business Info ─────────────────────────────────── */}
            <Text className="mb-4 text-xs font-bold uppercase tracking-wider text-gray-400">
              Business Information
            </Text>

            <Field label="Shop / Company Name" required>
              <StyledInput
                value={name}
                onChangeText={setName}
                placeholder="e.g. Ali AC Services"
                autoCapitalize="words"
                maxLength={150}
              />
            </Field>

            <Field label="Phone Number" required>
              <StyledInput
                value={phone}
                onChangeText={setPhone}
                placeholder="e.g. 0300-1234567"
                keyboardType="phone-pad"
                autoCapitalize="none"
                maxLength={20}
              />
            </Field>

            <Field
              label="WhatsApp Number"
              hint="Optional — leave blank if same as phone"
            >
              <StyledInput
                value={whatsapp}
                onChangeText={setWhatsapp}
                placeholder="e.g. 0300-1234567"
                keyboardType="phone-pad"
                autoCapitalize="none"
                maxLength={20}
              />
            </Field>

            <Field label="Description" hint="Optional — your experience, service areas, speciality">
              <StyledInput
                value={description}
                onChangeText={setDescription}
                placeholder="e.g. 10 years AC repair experience, serving G and F sectors"
                multiline
                numberOfLines={3}
                maxLength={500}
              />
            </Field>

            {/* ── Section: Service Category ──────────────────────────────── */}
            <Text className="mb-4 mt-2 text-xs font-bold uppercase tracking-wider text-gray-400">
              Service Category
            </Text>

            <Field label="What service do you provide?" required>
              <View className="flex-row flex-wrap gap-2">
                {CATEGORIES.map((cat) => {
                  const isSelected = category === cat.value;
                  return (
                    <Pressable
                      key={cat.value}
                      onPress={() => {
                        Haptics.selectionAsync();
                        setCategory(cat.value);
                      }}
                      className={`flex-row items-center gap-1.5 rounded-xl border px-3 py-2.5 active:opacity-80 ${
                        isSelected
                          ? 'border-orange-400 bg-orange-50'
                          : 'border-gray-200 bg-gray-50'
                      }`}
                    >
                      <Text>{cat.icon}</Text>
                      <Text
                        className={`text-sm font-semibold ${
                          isSelected ? 'text-orange-600' : 'text-gray-700'
                        }`}
                      >
                        {cat.label}
                      </Text>
                      {isSelected && (
                        <Ionicons name="checkmark-circle" size={14} color="#ea580c" />
                      )}
                    </Pressable>
                  );
                })}
              </View>
            </Field>

            {/* ── Section: Location ──────────────────────────────────────── */}
            <Text className="mb-4 mt-2 text-xs font-bold uppercase tracking-wider text-gray-400">
              Location
            </Text>

            <Field
              label="City"
              required
            >
              <StyledInput
                value={city}
                onChangeText={setCity}
                placeholder="e.g. Islamabad"
                autoCapitalize="words"
                maxLength={100}
              />
            </Field>

            <Field
              label="Area / Location"
              required
              hint="Type your area name (e.g. Barakaw, Bani Gala, G-13) or tap Use GPS"
              rightAction={
                <Pressable
                  onPress={handleUseGps}
                  className="flex-row items-center rounded-lg bg-orange-50 px-2.5 py-1 border border-orange-200/80 active:bg-orange-100"
                >
                  <Ionicons name="navigate" size={12} color="#EA580C" style={{ marginRight: 4 }} />
                  <Text className="text-xs font-semibold text-orange-700">
                    {isFetching ? 'Locating...' : 'Use My GPS'}
                  </Text>
                </Pressable>
              }
            >
              <View className="flex-row items-center gap-2 rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
                <Ionicons name="location-outline" size={18} color="#9CA3AF" />
                <TextInput
                  value={locationName}
                  onChangeText={(text) => {
                    setLocationName(text);
                    setGpsCoords(null); // Clear raw GPS if user typed manually
                  }}
                  placeholder='e.g. "Barakaw", "Bani Gala", or "G-13"'
                  placeholderTextColor="#9CA3AF"
                  autoCapitalize="words"
                  autoCorrect={false}
                  className="flex-1 text-[15px] text-gray-900"
                />
                {locationName.length > 0 && (
                  <Pressable
                    onPress={() => {
                      setLocationName('');
                      setGpsCoords(null);
                    }}
                  >
                    <Ionicons name="close-circle" size={16} color="#9CA3AF" />
                  </Pressable>
                )}
              </View>
            </Field>


            {/* ── Section: Verification ──────────────────────────────────── */}
            <Text className="mb-4 mt-2 text-xs font-bold uppercase tracking-wider text-gray-400">
              Verification
            </Text>

            <Field
              label="CNIC"
              required
              hint="National Identity Card number — for accountability"
            >
              <StyledInput
                value={cnic}
                onChangeText={setCnic}
                placeholder="e.g. 61101-1234567-1"
                autoCapitalize="none"
                keyboardType="numeric"
                maxLength={15}
              />
            </Field>

            <Field
              label="Business Registration Number"
              hint="Optional — official SECP or SMEDA registration"
            >
              <StyledInput
                value={businessReg}
                onChangeText={setBusinessReg}
                placeholder="e.g. SECP-2022-ISB-1234"
                autoCapitalize="characters"
                maxLength={50}
              />
            </Field>

            {/* ── Submit button ──────────────────────────────────────────── */}
            <View className="mt-4">
              <Pressable
                onPress={handleSubmit}
                disabled={isSubmitting}
                className={`items-center justify-center rounded-2xl py-4 ${
                  isSubmitting ? 'bg-orange-300' : 'bg-orange-500 active:bg-orange-600'
                }`}
              >
                {isSubmitting ? (
                  <View className="flex-row items-center gap-2">
                    <ActivityIndicator color="#fff" size="small" />
                    <Text className="text-base font-bold text-white">Registering…</Text>
                  </View>
                ) : (
                  <Text className="text-base font-bold text-white">Register My Shop ✓</Text>
                )}
              </Pressable>

              <Text className="mt-3 text-center text-xs text-gray-400">
                By registering, you agree to provide accurate information.
                Your CNIC is stored securely for verification only.
              </Text>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
}
