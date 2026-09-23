Build the mobile app for "Khidmat" — an AI service orchestrator for Pakistan's informal economy (plumbers, AC techs, electricians, tutors, beauticians). User types a request in English / Urdu / Roman Urdu, often code-mixed. Example: "Mujhe kal subah G-13 mein AC technician chahiye". An agent parses service + location + time, finds a nearby provider from a mock dataset, recommends one, books it, schedules a reminder. The backend isn't ready yet, so we're mocking the agent locally — same interface the real server will satisfy later.

This is chat-first. ONE text input. No form fields anywhere — no date picker, no map, no service dropdown, no location picker. Location and time come from the user's sentence; the agent extracts them. If the user doesn't say where, fall back to a default sector stored in Settings (default: F-10/3), or ask.

Stack you've got: Expo SDK 54, expo-router, TypeScript, NativeWind v4. zustand and @react-native-async-storage/async-storage are installed. Use NativeWind className everywhere, never StyleSheet. Brand color is orange #F97316, exposed as `primary` in tailwind.config.js — use bg-primary, text-primary, etc. Aesthetic: warm, rounded (rounded-2xl on cards), light theme, friendly. Think Foodpanda or Bykea — not Linear.

The current app/index.tsx is a NativeWind smoke test, replace it. The _layout.tsx is a bare Stack, replace with tab navigation. Leave app-example/ alone — that's reference material from the Expo reset.

# Folder layout

```
app/
  _layout.tsx                  # root, sets up tabs
  (tabs)/
    _layout.tsx                # bottom tab bar: Chat | Bookings | Settings
    index.tsx                  # Chat (default)
    bookings.tsx               # list
    settings.tsx
  bookings/
    [id].tsx                   # booking detail
components/
  ChatBubble.tsx
  ExtractedFieldsRow.tsx
  ProviderCard.tsx
  Button.tsx
  InputBar.tsx
  StatusBadge.tsx
  ExamplePromptChip.tsx
lib/
  agent/
    types.ts
    mockAgent.ts
  mock/
    providers.ts
  stores/
    useBookingsStore.ts
    useSettingsStore.ts
  util/
    distance.ts                # haversine
```

# Chat screen (the main one)

Empty state: greeting at the top — "Assalam-o-Alaikum 👋" then "What service do you need?" (large). Subtle subtitle below: "Type in English, Urdu, or Roman Urdu". Then 4 example chips that fill the input when tapped:

- "Mujhe kal subah G-13 mein AC technician chahiye"
- "Plumber abhi chahiye, bathroom mein leak hai"
- "Math tutor for my son, F-10"
- "Beautician chahiye Sunday ko, home service"

User sends a message → it appears as a right-aligned bubble (bg-primary, white text, rounded). Then the agent's response unfolds as a sequence of left-aligned bubbles (bg-gray-100, dark text), one per stage, each appearing 300–700ms apart:

1. Understanding bubble — "Got it, here's what I understood:" followed by a row of 3 pill chips: Service · Location · Time
2. Searching bubble — "Looking for [category] near [sector]..." with three animated dots
3. Ranking bubble — "Found N nearby. Ranking by distance, rating, and availability..."
4. Recommendation bubble — "Here's who I'd recommend:" followed by an embedded ProviderCard (provider name, category icon, distance like "2.1 km away", rating "★ 4.7 · 124 reviews", price range, one-line "Why this one" reason, primary Book button at the bottom of the card)

After the user taps Book:

5. Booking bubble — "Booking the 10:00 AM slot with [provider name]..." with dots
6. Confirmed bubble — green-tinted (bg-green-50, text-green-900) — "Confirmed! Your booking is set."
7. Reminder bubble — "I'll remind you at 9:00 AM tomorrow — 1 hour before your appointment."

End of thread: small footer line "View this booking in your Bookings tab →"

Sticky bottom input bar: multiline text input that auto-grows up to ~3 lines, then scrolls inside. Circular orange send button to the right with a paper-plane icon from @expo/vector-icons (already installed). Send button is disabled (gray) when the input is empty. Wrap in KeyboardAvoidingView with iOS behavior; Android is fine as-is.

Edge cases the chat needs to handle:

- Location missing AND Settings has a default → use the default and mention it in the understanding bubble's location chip (e.g. "F-10/3 (your home)")
- Location missing AND no default → agent emits awaiting_user with a location question. User replies in the next message; re-run extraction with the prior context, continue from there.
- Time missing → agent emits awaiting_user with a time question.
- Service category unknown → agent says "I help with AC repair, plumbing, electrical, tutoring, and beauty services. What do you need?"

# Bookings screen

List of past bookings, read from useBookingsStore (AsyncStorage-persisted). Each item is a rounded card: left has the category emoji/icon, middle has provider name (bold) + category + sector + scheduled time, right has a StatusBadge (colored pill — confirmed: blue, reminded: orange, completed: green, cancelled: gray). Tap → /bookings/[id].

Empty state: friendly centered text "No bookings yet" with a chip-button "Go to Chat" below that switches the tab.

Pull to refresh: just re-reads the store (it's local) but show the spinner briefly so it feels real.

# Booking detail (/bookings/[id])

Top: provider name (large bold), category, status badge. Then booking info section: time slot, location/sector, mock phone number with a tap-to-call (intent-only is fine, won't actually call in mock). Then a collapsible section titled "Why I picked this provider" — when expanded, render the preserved agent thread (the bubbles from the original conversation that produced this booking — yes, store these). Then a vertical status timeline: Confirmed (✓) → Reminder scheduled → Completed, with colored circles and a connecting line; current step highlighted. Bottom: red outline "Cancel booking" button with a confirm dialog; on confirm, updates status to 'cancelled'.

# Settings screen

Three stacked sections:

1. "Your default location" — text input with sector suggestions (typed string + dropdown filtered list of: F-6, F-7, F-8/1, F-8/2, F-10/1, F-10/3, F-11/1, F-11/3, G-9, G-10, G-11, G-13, I-8/3, I-9). Default value F-10/3. Saves to useSettingsStore on change. Helper text: "Used when you don't specify a location in your request."
2. "About Khidmat" — one paragraph: "Khidmat is an AI-powered service orchestrator. Tell me what you need in natural language — I'll find the right provider, book the slot, and follow up."
3. "Clear all bookings" — destructive red button with confirm dialog; on confirm, calls useBookingsStore.clear().

# Mock providers (lib/mock/providers.ts)

15 records total, 3 per category. Type:

```ts
export type ServiceCategory = 'ac' | 'plumber' | 'electrician' | 'tutor' | 'beautician';

export type Provider = {
  id: string;                  // 'p001'
  name: string;                // 'Ali AC Services'
  category: ServiceCategory;
  sector: string;              // 'G-13'
  coords: { lat: number; lng: number };
  rating: number;              // 4.7
  reviewCount: number;
  yearsExperience: number;
  priceRange: string;          // 'PKR 1500-3000'
  phone: string;               // '+92-300-1234567' (mock — don't use real numbers)
  availableSlots: string[];    // ['10:00 AM', '2:00 PM', '6:00 PM'] — for tomorrow
};
```

Sector coords to use (sector-center is fine, doesn't have to be precise to the meter):
F-6 (33.7295, 73.0775), F-7 (33.7170, 73.0707), F-10 (33.6938, 73.0162), F-11 (33.6840, 73.0040), G-9 (33.6800, 72.9870), G-10 (33.6840, 72.9820), G-11 (33.6620, 72.9760), G-13 (33.6470, 72.9510), I-8 (33.6620, 73.0790), I-9 (33.6520, 73.0700).

Names should sound Pakistani + category-relevant. Examples: "Ali AC Services", "CoolFix Islamabad", "Khan Cooling Solutions" / "Sajid Plumbing", "QuickFix Plumbers", "Ahsan Sanitary Works" / "Bilal Electric Works", "PowerPro Services", "Faisal Electricals" / "Ayesha Math Academy", "Hammad Tutors", "STEM Bright Tutors" / "Maria Beauty Salon", "Glow Home Service", "Saima at-Home Beauty". Spread them across sectors. Make sure G-13 has at least one AC provider with a 10:00 AM slot so the canonical scenario gives a clean result.

# Mock agent (lib/agent/mockAgent.ts + types.ts)

This is the brain. The interface needs to stay stable so it can be swapped for the real server later.

types.ts:

```ts
import type { Provider, ServiceCategory } from '../mock/providers';

export type ExtractedIntent = {
  service: ServiceCategory | null;
  location: string | null;     // sector like 'G-13' or null
  time: string | null;         // human-readable: 'tomorrow morning' or null
  resolvedSlot: string | null; // concrete: '10:00 AM' after resolution
};

export type AgentEvent =
  | { type: 'understanding'; extracted: ExtractedIntent; usedDefaultLocation: boolean }
  | { type: 'searching'; near: string; category: ServiceCategory }
  | { type: 'ranking'; candidateCount: number }
  | { type: 'recommendation'; provider: Provider; distanceKm: number; reasoning: string; suggestedSlot: string }
  | { type: 'awaiting_user'; question: string; missing: 'location' | 'time' | 'service' }
  | { type: 'booking'; provider: Provider; slot: string }
  | { type: 'confirmed'; bookingId: string }
  | { type: 'reminder_scheduled'; at: string };
```

mockAgent.ts exports two async generators:

```ts
export async function* runAgent(
  userMessage: string,
  context: { defaultLocation: string; conversationHistory: AgentEvent[] }
): AsyncGenerator<AgentEvent>;

export async function* confirmBooking(
  provider: Provider,
  slot: string
): AsyncGenerator<AgentEvent>;
```

runAgent flow:

1. Parse the message with simple keyword/regex matching — this is a mock, don't over-engineer:
   - service: keyword tables per category (see below)
   - location: regex /\b[A-I]-\d{1,2}(?:\/\d)?\b/i
   - time: keywords — "kal"/"tomorrow", "subah"/"morning", "shaam"/"evening", "raat"/"night", "abhi"/"now"/"asap", "aaj"/"today", weekday names
2. yield { type: 'understanding', extracted, usedDefaultLocation }. Await ~500ms.
3. Branching:
   - service null → yield awaiting_user(missing: 'service'), return.
   - location null AND no defaultLocation → yield awaiting_user(missing: 'location'), return.
   - location null AND defaultLocation present → use defaultLocation, set usedDefaultLocation=true in the understanding event.
   - time null → yield awaiting_user(missing: 'time'), return.
4. yield searching, await ~700ms.
5. Filter providers by category. For each, compute distance from user's effective location to provider.coords using haversine (lib/util/distance.ts). Sort by composite score: lower distance better, higher rating better, has any availableSlot in next 24h better. yield ranking with candidateCount.
6. yield recommendation with top pick. The reasoning is one short sentence like "Closest available technician with 4.7★ from 124 reviews." suggestedSlot is the first availableSlot of the picked provider.

The generator ends after recommendation. When the user taps Book on the ProviderCard, the Chat screen calls confirmBooking(provider, slot), which yields:

- yield { type: 'booking', provider, slot }, await ~1000ms
- yield { type: 'confirmed', bookingId: `b_${Date.now()}` }
- yield { type: 'reminder_scheduled', at: '...' } — compute 1 hour before slot, format like '9:00 AM'

The Chat screen consumes both generators with for-await-of, appending each yielded event as a new bubble. When the recommendation event comes through, render a ProviderCard inside that bubble with onBook wired to call confirmBooking with that provider + suggestedSlot.

Service keyword matching (case-insensitive, match any):

- ac: "ac", "air condition", "cooling"
- plumber: "plumb", "leak", "tap", "nal", "pipe", "bathroom"
- electrician: "electric", "wiring", "bijli", "switch", "fan"
- tutor: "tutor", "teach", "tuition", "math", "english", "science", "ustaad"
- beautician: "beautician", "salon", "beauty", "makeup", "facial", "hair", "haircut"

# Stores

useBookingsStore — zustand with persist middleware backed by AsyncStorage (createJSONStorage(() => AsyncStorage)).

```ts
type Booking = {
  id: string;
  providerId: string;
  providerName: string;
  category: ServiceCategory;
  sector: string;
  scheduledFor: string;       // 'Tomorrow, 10:00 AM'
  scheduledTimestamp: number;
  status: 'confirmed' | 'reminded' | 'completed' | 'cancelled';
  reminderAt: string;
  agentThread: AgentEvent[];  // preserved events from the conversation that produced this booking
  createdAt: number;
};
```

State: { bookings: Booking[] }. Actions: addBooking(b), updateStatus(id, status), cancel(id), clear(). Selectors: getById(id), allSortedByDate() returning newest first.

useSettingsStore — zustand with persist + AsyncStorage. State: { defaultLocation: string } — initial 'F-10/3'. Action: setDefaultLocation(s).

# Components

Small, NativeWind className only, no StyleSheet:

- ChatBubble — props { side: 'user' | 'agent', tone?: 'default' | 'success', children }. User: right-aligned, bg-primary, text-white. Agent default: left-aligned, bg-gray-100, text-gray-900. Agent success: bg-green-50, text-green-900.
- ExtractedFieldsRow — props { service, location, time }. Renders 3 pill chips horizontally with a small icon per field.
- ProviderCard — props { provider, distanceKm, reasoning, suggestedSlot, onBook }. White card, rounded-2xl, subtle shadow, padding-4, primary Book button at the bottom.
- Button — props { variant: 'primary' | 'secondary' | 'destructive', onPress, children, disabled? }.
- InputBar — props { value, onChangeText, onSend, placeholder, disabled }. Sticky bottom, multiline input + circular send button.
- StatusBadge — props { status }. Colored rounded pill matching the status colors above.
- ExamplePromptChip — props { text, onPress }. Light orange (bg-primary-100), rounded pill, dark text.

# Done when

App launches on Chat with the greeting and 4 chips. Tapping the canonical chip ("Mujhe kal subah G-13 mein AC technician chahiye") and sending produces the full agent thread end-to-end (understanding → search → rank → recommend with ProviderCard → after Book tap → booking → confirmed → reminder). The new booking appears in the Bookings tab; its detail screen shows the preserved agent thread under "Why I picked this provider".

Missing-info scenarios work:
- "Plumber chahiye" (no location, no time) — uses Settings default location, asks for time
- "AC technician kal subah" (no location, default cleared from Settings) — asks for location
- "Mujhe haircut chahiye" — maps to beautician
- "I need a unicorn trainer" — gets the unknown-category response

Settings default location persists across app restarts (kill the process, reopen, value is still there). Clear-all empties the bookings list. Orange primary color used consistently. No console errors. Runs in Expo Go via `npx expo start`.

# Don't bother with

Real LLM calls. Real GPS / location services. Real notifications (reminder bubbles are visual only). Any map UI. Voice / mic input. Auth or accounts. Splash or onboarding. A separate provider profile screen (the inline ProviderCard is enough). i18n libraries (UI chrome stays English; we accept multilingual input only). Heavy animations beyond fade-in and the dot loader. iOS or web polish (target Android via Expo Go).

# When done

Run `npx expo start --clear` and verify the above on a real Android phone via Expo Go. If you deviated from anything in this brief, jot a few lines in IMPLEMENTATION_NOTES.md at the project root explaining what and why. Don't commit — leave that for the human.
