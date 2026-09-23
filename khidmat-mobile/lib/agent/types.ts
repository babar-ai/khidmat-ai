import type { Provider, ServiceCategory } from '../mock/providers';

export type ExtractedIntent = {
  service: ServiceCategory | null;
  location: string | null; // sector like 'G-13' or null
  time: string | null; // human-readable: 'tomorrow morning' or null
  resolvedSlot: string | null; // concrete: '10:00 AM' after resolution
};

export type AgentEvent =
  | {
      type: 'understanding';
      extracted: ExtractedIntent;
      usedDefaultLocation: boolean;
    }
  | { type: 'searching'; near: string; category: ServiceCategory }
  | { type: 'ranking'; candidateCount: number }
  | {
      type: 'recommendation';
      provider: Provider;
      distanceKm: number;
      reasoning: string;
      suggestedSlot: string;
      dayLabel: string; // 'Today' | 'Tomorrow' | 'Monday' | ...
      scheduledTimestamp: number;
    }
  | {
      type: 'awaiting_user';
      question: string;
      missing: 'location' | 'time' | 'service';
    }
  | { type: 'booking'; provider: Provider; slot: string }
  | { type: 'confirmed'; bookingId: string }
  | { type: 'reminder_scheduled'; at: string };
