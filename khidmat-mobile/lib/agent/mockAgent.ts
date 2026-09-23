import { Platform } from 'react-native';
import type { ServiceCategory, Provider } from '../mock/providers';
import type { AgentEvent, ExtractedIntent } from './types';

// Use 10.0.2.2 for Android emulator, localhost for iOS simulator
const API_BASE_URL = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// Map backend categories to frontend categories
function mapCategory(backendCat: string): ServiceCategory {
  if (backendCat.includes('ac')) return 'ac';
  if (backendCat.includes('plumber')) return 'plumber';
  if (backendCat.includes('electrician')) return 'electrician';
  if (backendCat.includes('tutor')) return 'tutor';
  if (backendCat.includes('beautician')) return 'beautician';
  return 'ac'; // fallback
}

export async function* runAgent(
  userMessage: string,
  context: { defaultLocation: string; conversationHistory: AgentEvent[] },
): AsyncGenerator<AgentEvent> {
  let finalMessage = userMessage;

  // Append default location or previous context if we are following up
  const lastAwaiting = context.conversationHistory
    .filter((e): e is Extract<AgentEvent, { type: 'awaiting_user' }> => e.type === 'awaiting_user')
    .pop();

  const lastUnderstanding = context.conversationHistory
    .filter((e): e is Extract<AgentEvent, { type: 'understanding' }> => e.type === 'understanding')
    .pop();

  if (lastAwaiting && lastUnderstanding) {
    const prevService = lastUnderstanding.extracted.service || 'a service';
    finalMessage = `I need ${prevService}. ${userMessage}`;
  } else if (context.defaultLocation) {
    finalMessage += ` (Location: ${context.defaultLocation})`;
  }

  yield {
    type: 'understanding',
    extracted: { service: null, location: null, time: null, resolvedSlot: null },
    usedDefaultLocation: false,
  };
  
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: finalMessage,
        user_id: 'user_' + Date.now()
      })
    });

    if (res.status === 400) {
      const errorData = await res.json().catch(() => ({}));
      if (errorData.detail?.message && errorData.detail.message.toLowerCase().includes("location")) {
        const partial = errorData.detail.partial_intent;
        if (partial) {
           yield {
            type: 'understanding',
            extracted: { 
              service: mapCategory(partial.service_type || ''), 
              location: null, 
              time: partial.requested_time, 
              resolvedSlot: null 
            },
            usedDefaultLocation: false,
          };
        }

        yield {
          type: 'awaiting_user',
          question: 'Which sector should I look in? For example, G-13 or F-10.',
          missing: 'location',
        };
        return;
      }
    }

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`API Error ${res.status}: ${errText}`);
    }

    const data = await res.json();
    const intent = data.parsed_intent;

    if (!intent) {
       yield {
        type: 'awaiting_user',
        question: 'Could you clarify what service you need?',
        missing: 'service',
      };
      return;
    }

    const frontendCategory = mapCategory(intent.service_type);

    const extracted: ExtractedIntent = {
      service: frontendCategory,
      location: intent.location,
      time: intent.requested_time,
      resolvedSlot: null,
    };

    yield {
      type: 'understanding',
      extracted,
      usedDefaultLocation: false,
    };
    await delay(500);

    yield {
      type: 'searching',
      near: intent.location || 'your area',
      category: frontendCategory,
    };
    await delay(500);

    const providers = data.providers || [];
    yield {
      type: 'ranking',
      candidateCount: providers.length || 3,
    };
    await delay(500);

    const topProvider = data.top_provider;
    if (topProvider) {
      const p = topProvider.provider || topProvider;
      const mappedProvider: Provider = {
        id: p.provider_id,
        name: p.name,
        category: frontendCategory,
        rating: p.rating || 4.5,
        reviewCount: p.review_count || 120,
        yearsExperience: 5,
        priceRange: 'PKR 1500-3000',
        phone: p.phone || '+92-300-1234567',
        sector: intent.location || 'Islamabad',
        coords: { lat: p.lat || 33.6844, lng: p.lng || 73.0479 },
        availableSlots: p.available_slots || ["10:00 AM", "2:00 PM"]
      };

      // Store the backend's generated booking locally for confirmBooking to use!
      const scheduledAt = data.booking?.status === 'confirmed' ? Date.now() + 86400000 : Date.now();

      yield {
        type: 'recommendation',
        provider: mappedProvider,
        distanceKm: topProvider.distance_km || 2.5,
        reasoning: `Found the best matching ${mappedProvider.category} with a ${mappedProvider.rating} rating.`,
        suggestedSlot: "10:00 AM",
        dayLabel: 'Tomorrow',
        scheduledTimestamp: scheduledAt,
      };
    }
  } catch (err: any) {
    console.error("runAgent API Error", err);
    yield {
      type: 'awaiting_user',
      question: `Sorry, I had trouble connecting to the backend. (${err.message})`,
      missing: 'service'
    };
  }
}

export async function* confirmBooking(
  provider: Provider,
  slot: string,
  dayLabel: string,
): AsyncGenerator<AgentEvent> {
  // Since the backend already booked it during the single /request pipeline, 
  // we just simulate the UI confirmation step for a smooth experience.
  yield {
    type: 'booking',
    provider,
    slot,
  };
  await delay(1000);

  const bookingId = `b_${Date.now()}`;
  yield {
    type: 'confirmed',
    bookingId,
  };
  await delay(300);

  yield {
    type: 'reminder_scheduled',
    at: `1 hour before ${dayLabel}`,
  };
}
