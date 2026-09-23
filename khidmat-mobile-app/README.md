# Khidmat — Mobile

Chat-first mobile client for the Khidmat AI service orchestrator. The user types what they need ("AC stopped working in G-13, need someone today") and the in-app agent walks through understanding → searching → ranking → recommending → booking, narrating each step as a chat thread.

Built with Expo, React Native, Zustand, and TypeScript. Pairs with any server that implements the [wire contract](#wire-contract) below.

## Status

Currently runs against an in-process mock agent at [lib/agent/mockAgent.ts](lib/agent/mockAgent.ts). Wiring to a real backend is the next integration step — swap the mock for an SSE client that hits `EXPO_PUBLIC_API_BASE_URL/chat`.

## Stack

| Layer | Tech |
|-------|------|
| Framework | Expo SDK 54 + Expo Router |
| Runtime | React Native 0.81.5, React 19 |
| Styling | NativeWind + Tailwind |
| State | Zustand + AsyncStorage (persisted) |
| Language | TypeScript (strict) |

## Screens

| Route | Purpose |
|-------|---------|
| `app/(tabs)/index.tsx` | Chat — single input; agent reasoning unfolds as a thread |
| `app/(tabs)/bookings.tsx` | Bookings list (from AsyncStorage) |
| `app/bookings/[id].tsx` | Booking detail + preserved agent reasoning + cancel |
| `app/(tabs)/settings.tsx` | Default location + about + clear-all |

## Local development

Prerequisites: Node 20, npm, Expo Go on your phone (or an Android/iOS simulator).

```bash
cp .env.example .env
# Edit .env if your server is on a different host/port
npm install
npx expo start --clear
```

Scan the QR with Expo Go (Android) or the Camera app (iOS). When running on a physical device, set `EXPO_PUBLIC_API_BASE_URL` to your machine's LAN IP — `localhost` will not resolve.

### Scripts

| Script | What |
|--------|------|
| `npm start` | `expo start` — Metro dev server |
| `npm run android` | Build & open on connected Android device |
| `npm run ios` | iOS simulator (macOS only) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | Expo ESLint |

## Environment variables

| Var | Required | Default | Purpose |
|-----|----------|---------|---------|
| `EXPO_PUBLIC_API_BASE_URL` | yes | `http://localhost:5000` | Base URL of the Khidmat server. |

## State / persistence

The mobile app is the source of truth for bookings:

- `useBookingsStore` persists to AsyncStorage under the `khidmat-bookings` key.
- Every `/chat` request sends the FE's current bookings to the server as context.
- The server emits `booking_update` / `booking_cancel` / `booking_query` events as *intents*; the FE validates and applies them locally.
- Change servers and the user's bookings stay put.

## Wire contract

Pairs with any server that implements this. See [lib/agent/types.ts](lib/agent/types.ts) for the authoritative TypeScript shapes.

### Request: `POST /chat`

```ts
{
  message: string,            // user input, any language
  sessionId?: string,         // UUID per chat thread; omit for one-shot
  defaultLocation?: string,   // sector from Settings, e.g. 'G-13'
  bookings?: Booking[],       // FE's persisted bookings
}
```

### Response: SSE stream of `AgentEvent`

Content-Type `text/event-stream`, one `AgentEvent` per `data:` frame. Event types:

- `thought` — agent narration (interleaved across flows)
- `understanding`, `searching`, `ranking`, `recommendation`, `booking`, `confirmed`, `reminder_scheduled` — new-booking flow
- `awaiting_user` — pause and ask; FE resends with same `sessionId` to resume
- `booking_update`, `booking_cancel`, `booking_query` — intents to mutate existing bookings (FE applies)

Exact shapes: [lib/agent/types.ts](lib/agent/types.ts). When pairing with a partner's server, this file is the integration spec.

## Multilingual

Inputs in English, Urdu, Roman Urdu, or mixed are accepted — the LLM behind the server handles them natively. `awaiting_user` follow-up questions render in English regardless of input language (server-side limitation).

## Limitations

- No authentication; single anonymous user.
- Provider catalog is a 15-entry mock for Islamabad sectors only (no Maps integration).
- Reminders are scheduled as local notifications by the FE; no push/SMS infra.
- Typecheck and lint only; no test suite.

## How Antigravity was used

Google Antigravity was the AI coding assistant that wrote the mobile screens, components, and state stores from prescriptive prompts authored by the developer. Build-time only — Antigravity is not part of the runtime. Prompt history: [docs/antigravity-prompts/](docs/antigravity-prompts/).
