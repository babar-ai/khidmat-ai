/**
 * API client for the Khidmat backend.
 *
 * Wraps the real FastAPI backend at EXPO_PUBLIC_API_BASE_URL.
 * Attaches device GPS coordinates automatically from the location store
 * so every request has user_lat / user_lng when available.
 */

import { Platform } from 'react-native';
import Constants from 'expo-constants';
import { useLocationStore } from '@/lib/stores/useLocationStore';

/**
 * Resolves the backend API base URL.
 * Automatically adapts for Android (physical device via Metro IP or emulator via 10.0.2.2)
 * so it never fails with "failed to connect to localhost/127.0.0.1:8000".
 */
export function getApiBaseUrl(): string {
  // Extract Metro bundler host IP if available (e.g. 192.168.0.106)
  const hostUri = Constants.expoConfig?.hostUri;
  const metroHost = hostUri ? hostUri.split(':')[0] : null;

  // When running via Expo Go on Android or iOS, Metro's host IP is the exact PC running FastAPI
  if (metroHost && Platform.OS !== 'web') {
    return `http://${metroHost}:8000`;
  }

  let url = (process.env.EXPO_PUBLIC_API_BASE_URL ?? '').trim();
  if (url && !url.includes('localhost') && !url.includes('127.0.0.1')) {
    return url.replace(/\/$/, '');
  }

  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }

  return 'http://localhost:8000';
}

// ── Types mirroring backend schemas ─────────────────────────────────────────

export type ServiceRequestPayload = {
  text: string;
  user_id: string;
  user_lat?: number | null;
  user_lng?: number | null;
  session_id?: string | null;
};


export type IntentResult = {
  service_type: string;
  location_text: string | null;
  scheduled_text: string | null;
  language: string;
  confidence: number;
};

export type ProviderSummary = {
  id: number;
  name: string;
  city: string;
  category: string;
  rating: number;
  distance_km: number | null;
};

export type BookingRead = {
  id: number;
  session_id: string;
  user_id: string;
  provider_id: number;
  service_type: string;
  location_text: string | null;
  scheduled_at: string | null;
  booking_code: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type TraceStep = {
  step: number;
  agent: string;
  action: string;
  input_summary: string | null;
  output_summary: string | null;
  duration_ms: number | null;
};

export type ServiceResponse = {
  session_id: string;
  intent: IntentResult;
  provider: ProviderSummary;
  booking: BookingRead;
  trace: TraceStep[];
  message: string;
};

export type ErrorResponse = {
  error: string;
  detail: string;
  session_id: string | null;
};

// ── API Functions ─────────────────────────────────────────────────────────────

/**
 * POST /api/v1/request
 *
 * Sends the user's natural language text to the backend agent pipeline.
 * Automatically attaches the user's GPS coordinates from the location store.
 */
export async function sendServiceRequest(
  text: string,
  userId: string,
): Promise<ServiceResponse> {
  // Grab the latest GPS fix from the store (may be null if permission denied)
  const { coordinates } = useLocationStore.getState();

  const payload: ServiceRequestPayload = {
    text,
    user_id: userId,
    user_lat: coordinates?.latitude ?? null,
    user_lng: coordinates?.longitude ?? null,
  };

  const response = await fetch(`${getApiBaseUrl()}/api/v1/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = (await response.json()) as ErrorResponse;
    throw new Error(errorBody.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<ServiceResponse>;
}

/**
 * GET /api/v1/booking/{id}
 */
export async function getBooking(bookingId: number): Promise<BookingRead> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/booking/${bookingId}`);

  if (!response.ok) {
    throw new Error(`Booking not found (status ${response.status})`);
  }

  return response.json() as Promise<BookingRead>;
}

/**
 * GET /api/v1/trace/{session_id}
 */
export async function getTrace(sessionId: string): Promise<TraceStep[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/trace/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Trace not found (status ${response.status})`);
  }

  const data = await response.json();
  return data.steps as TraceStep[];
}


/**
 * GET /health — backend liveness probe
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/health`, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}

// ── Provider Registration ──────────────────────────────────────────────────────

export type ProviderRegisterPayload = {
  name: string;
  phone: string;
  whatsapp_number?: string;
  city: string;
  category: string;
  location_name?: string;      // human-readable, e.g. "G-13, Islamabad"
  latitude?: number;
  longitude?: number;
  description?: string;
  cnic: string;
  business_reg_number?: string;
};

export type ProviderRead = {
  id: number;
  name: string;
  phone: string;
  whatsapp_number: string | null;
  city: string;
  category: string;
  latitude: number;
  longitude: number;
  description: string | null;
  business_reg_number: string | null;
  rating: number;
  reviews_count: number;
  is_active: boolean;
};

/**
 * POST /api/v1/provider/register
 *
 * Registers a new service provider.
 * Accepts either location_name (geocoded automatically) or raw lat/lng.
 */
export async function registerProvider(payload: ProviderRegisterPayload): Promise<ProviderRead> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/provider/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body?.detail;
    if (typeof detail === 'string') throw new Error(detail);
    if (typeof detail === 'object') throw new Error(detail?.msg ?? JSON.stringify(detail));
    throw new Error(`Registration failed (status ${response.status})`);
  }

  return response.json() as Promise<ProviderRead>;
}


