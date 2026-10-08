/**
 * lib/agent/realAgent.ts
 *
 * Replaces mockAgent.ts — calls the real Khidmat FastAPI backend.
 * Emits AgentEvent stream so the UI (index.tsx) works without any changes.
 *
 * API response shape (from POST /api/v1/request):
 * {
 *   session_id, message,
 *   intent:   { service_type, location_text, scheduled_text, language, confidence },
 *   provider: { id, name, city, category, rating, distance_km },
 *   booking:  { id, booking_code, status, ... },
 *   trace:    [ { step, agent, action, ... } ]
 * }
 */

import type { ServiceCategory, Provider } from '../mock/providers';
import type { AgentEvent, ExtractedIntent } from './types';
import { useLocationStore } from '../stores/useLocationStore';
import { getApiBaseUrl } from '../api/khidmatApi';

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}


/**
 * Map backend category strings to frontend ServiceCategory type.
 * Backend uses: ac_technician | plumber | electrician | carpenter | cleaner | painter
 * Frontend uses: ac | plumber | electrician | tutor | beautician
 */
function mapCategory(backendCat: string): ServiceCategory {
  if (backendCat.includes('ac')) return 'ac';
  if (backendCat.includes('plumber')) return 'plumber';
  if (backendCat.includes('electrician')) return 'electrician';
  if (backendCat.includes('carpenter')) return 'electrician'; // closest frontend type
  if (backendCat.includes('cleaner')) return 'beautician';   // closest frontend type
  if (backendCat.includes('painter')) return 'electrician';  // closest frontend type
  return 'ac'; // fallback
}

// ── Active conversational thread ID (persisted in PostgreSQL via LangGraph) ──
let activeSessionId: string | null = null;

export function resetConversationSession() {
  activeSessionId = null;
}

export async function* runAgent(
  userMessage: string,
  context: { defaultLocation: string; conversationHistory: AgentEvent[] },
): AsyncGenerator<AgentEvent> {
  // Ensure we have a persistent session ID across turns
  if (!activeSessionId) {
    activeSessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
  }

  // Get GPS from store (may be null)
  const { coordinates } = useLocationStore.getState();

  try {
    const res = await fetch(`${getApiBaseUrl()}/api/v1/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: userMessage,
        user_id: 'user_mobile',
        user_lat: coordinates?.latitude ?? null,
        user_lng: coordinates?.longitude ?? null,
        session_id: activeSessionId,
      }),
    });

    // ── Handle clarification / follow-up question / greeting (HTTP 400) ───────
    if (res.status === 400) {
      const errorData = await res.json().catch(() => ({}));
      const detail = errorData?.detail;
      const message: string =
        typeof detail === 'string'
          ? detail
          : (detail?.message ?? detail?.detail ?? '');

      if (detail && typeof detail === 'object' && detail?.session_id) {
        activeSessionId = detail.session_id;
      }

      // If backend asks a follow-up question, greeting, or conversational reply
      if (
        detail &&
        typeof detail === 'object' &&
        (detail?.is_greeting ||
          detail?.error === 'greeting' ||
          detail?.error === 'awaiting_input' ||
          detail?.error === 'conversation' ||
          detail?.dialogue_act ||
          detail?.missing_slots)
      ) {
        yield {
          type: 'awaiting_user',
          question: message,
          missing: detail?.missing_slots?.[0] ?? 'service',
        };
        return;
      }

      // Fallback follow-up message
      yield {
        type: 'awaiting_user',
        question: message || 'Could you provide a few more details so I can match you with the right provider?',
        missing: 'service',
      };
      return;
    }

    if (!res.ok) {
      throw new Error(`API Error ${res.status}: ${await res.text()}`);
    }

    // ── Success: Recommendation / Booking confirmed ─────────────────────────
    // Keep activeSessionId alive so post-recommendation conversation (objections,
    // questions, confirmations) preserves context in LangGraph checkpoint
    const data = await res.json();
    if (data.session_id) {
      activeSessionId = data.session_id;
    }

    const intent  = data.intent;    // ← real field name (not "parsed_intent")
    const providerData = data.provider; // ← real field name (not "top_provider")

    if (!intent || !intent.service_type) {
      yield {
        type: 'awaiting_user',
        question: 'Could you clarify what service you need?',
        missing: 'service',
      };
      return;
    }

    const frontendCategory = mapCategory(intent.service_type);

    // ── Step 1: Show searching ──────────────────────────────────────────────
    yield {
      type: 'searching',
      near: intent.location_text ?? context.defaultLocation ?? 'your area',
      category: frontendCategory,
    };
    await delay(400);

    // ── Step 3: Show ranking ────────────────────────────────────────────────
    yield { type: 'ranking', candidateCount: 1 };
    await delay(400);

    // ── Step 4: Show recommendation ─────────────────────────────────────────
    if (providerData) {
      const mappedProvider: Provider = {
        id:              String(providerData.id),           // ← real field (not "provider_id")
        name:            providerData.name,
        category:        frontendCategory,
        rating:          providerData.rating ?? 0,
        reviewCount:     0,                                 // not in ProviderSummary — set to 0
        yearsExperience: 0,
        priceRange:      'PKR 800-3000',
        phone:           '',                                // not in ProviderSummary
        sector:          providerData.city ?? 'Islamabad',
        coords:          { lat: 33.6844, lng: 73.0479 },   // default Islamabad center
        availableSlots:  ['10:00 AM', '2:00 PM', '5:00 PM'],
      };

      const scheduledSlot = intent.scheduled_text || 'Tomorrow, 10:00 AM';

      yield {
        type: 'recommendation',
        provider:          mappedProvider,
        distanceKm:        providerData.distance_km ?? 0,  // ← real field
        reasoning:         `Top-rated ${mappedProvider.category.replace('_', ' ')} nearby with a ${mappedProvider.rating} star rating.`,
        suggestedSlot:     scheduledSlot,
        dayLabel:          'Scheduled',
        scheduledTimestamp: Date.now() + 86_400_000, // tomorrow
      };

      // ── Step 5: If backend confirmed a booking, stream confirmed events ─────
      if (data.booking) {
        await delay(500);
        yield {
          type: 'booking',
          provider: mappedProvider,
          slot: scheduledSlot,
        };
        await delay(400);

        yield {
          type: 'confirmed',
          bookingId: data.booking.booking_code ?? `b_${data.booking.id}`,
        };
        await delay(200);

        yield {
          type: 'reminder_scheduled',
          at: `1 hour before ${scheduledSlot}`,
        };
      }
    }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error';
    console.error('runAgent API Error', err);
    yield {
      type: 'awaiting_user',
      question: `Sorry, I couldn't reach the server. (${message})`,
      missing: 'service',
    };
  }
}

// ── Booking confirmation ─────────────────────────────────────────────────────
// The backend books automatically during /request.
// This just streams the UI confirmation steps for a smooth experience.

export async function* confirmBooking(
  provider: Provider,
  slot: string,
  dayLabel: string,
): AsyncGenerator<AgentEvent> {
  yield { type: 'booking', provider, slot };
  await delay(800);

  yield { type: 'confirmed', bookingId: `b_${Date.now()}` };
  await delay(300);

  yield { type: 'reminder_scheduled', at: `1 hour before ${dayLabel} ${slot}` };
}
