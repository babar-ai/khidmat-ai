/**
 * API client for the Khidmat backend.
 *
 * Wraps the real FastAPI backend at EXPO_PUBLIC_API_BASE_URL.
 * Attaches device GPS coordinates automatically from the location store
 * so every request has user_lat / user_lng when available.
 */

import { useLocationStore } from '@/lib/stores/useLocationStore';

const BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://10.0.2.2:8000').replace(/\/$/, '');

// ── Types mirroring backend schemas ─────────────────────────────────────────

export type ServiceRequestPayload = {
  text: string;
  user_id: string;
  user_lat?: number | null;
  user_lng?: number | null;
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

  const response = await fetch(`${BASE_URL}/api/v1/request`, {
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
  const response = await fetch(`${BASE_URL}/api/v1/booking/${bookingId}`);

  if (!response.ok) {
    throw new Error(`Booking not found (status ${response.status})`);
  }

  return response.json() as Promise<BookingRead>;
}

/**
 * GET /api/v1/trace/{session_id}
 */
export async function getTrace(sessionId: string): Promise<TraceStep[]> {
  const response = await fetch(`${BASE_URL}/api/v1/trace/${sessionId}`);

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
    const response = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return response.ok;
  } catch {
    return false;
  }
}
