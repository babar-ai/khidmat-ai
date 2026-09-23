Hey — went through what you built and cleaned up a bunch of stuff myself.

Fixed the typed-route error in `app/(tabs)/bookings.tsx`. Wired the extracted time through the agent so `scheduledFor` actually reflects what the user said ("Today" / "Tomorrow" / "Monday") instead of being hardcoded to "Tomorrow" — there's a `resolveSchedule()` helper in `lib/agent/mockAgent.ts` now and the recommendation event carries `dayLabel` + `scheduledTimestamp`. Killed the Zustand infinite-loop on the Bookings tab (the `allSortedByDate` selector was returning a fresh array every render, blowing up `useSyncExternalStore`) — moved sorting into a `useMemo` in the component, dropped derived methods off the store. Added a "Mark as completed" button on booking detail that advances the status timeline. Settings sector input only commits on blur/select now, not on every keystroke. Added `expo-haptics` on Send + booking confirm. `app.json` is rebranded to Khidmat. `tsconfig.json` + `eslint.config.js` exclude `app-example/`.

App boots, chat flow works end-to-end, typecheck + lint are clean.

Three things left I want you to do:

---

**1. Add a "new chat" / clear chat option**

There's no way to reset the conversation right now. Once you've booked something the chat thread sticks around forever (it's local state, fine on reload, but mid-session you can't start fresh).

Add a small button in the Chat screen header — top-right of the "Khidmat / Your AI service assistant" header in `app/(tabs)/index.tsx`. Use an Ionicons icon, something like `create-outline` or `refresh-outline`, pick whichever looks right.

When tapped:
- If `messages.length === 0`, do nothing (button can also just be hidden in that case)
- Otherwise, show a confirm Alert ("Start a new chat? This clears the current conversation."), and on confirm reset `messages`, `agentEvents`, `agentEventsRef.current`, `inputText`, and make sure `isProcessing` is false
- Bookings in the Bookings tab stay untouched — they're already persisted

Don't add a separate header component for this, just slot the button into the existing header View on the right side.

---

**2. Booking detail header collides with the status bar / notch on Android**

When you open a booking from the list, the "Booking Details" header + back arrow render *underneath* the device status bar (time, wifi, battery). They overlap. Looks broken.

The other tabs are fine because they use `<SafeAreaView edges={['top']}>`. The booking detail uses the Stack header from `app/_layout.tsx` (`bookings/[id]` route) and the screen body is just a `ScrollView` — no safe-area wrapper.

This is because `app.json` has `"edgeToEdgeEnabled": true` for Android, which makes the system bars translucent and the Stack header doesn't auto-pad for them in this config.

Fix it properly. The right approach (don't just disable edge-to-edge — that flag is there for a reason and the other tabs look good with it):

- In `app/_layout.tsx`, the Stack screenOptions / the `bookings/[id]` screen options need to be status-bar aware. Check the expo-router native-stack header options — there's typically a `statusBarTranslucent` / safe-area inset prop, or you may need to add `import { SystemBars } from 'react-native-edge-to-edge'` handling
- OR wrap the ScrollView in `app/bookings/[id].tsx` with `<SafeAreaView edges={['top']}>` from `react-native-safe-area-context` and configure the Stack header for that route to be safe-area-inset friendly

Test on an Android device with a notch (that's where the bug shows up). Don't regress the iOS header — it likely already looks fine there.

Read the expo-router v6 + SDK 54 docs on `withLayoutContext` / native-stack header before guessing. https://docs.expo.dev/versions/v54.0.0/

---

**3. Animated typing dots are breaking out of the chat bubble**

The `DotsLoader` in `app/(tabs)/index.tsx` is rendered *inside* the agent bubble for `searching`, `ranking`, and `booking` events, sitting next to the text in a `flex-row`. Visually the dots end up escaping the bubble or wrapping badly when the text is long. Looks janky.

Pick the cleanest fix — preference order:

a) **Put the dots in their own small pill-bubble below the text bubble** (WhatsApp / iMessage typing-indicator style). The text bubble shows "Looking for AC Technician near G-13", and beneath it a tiny separate bubble shows just the three animated dots. This reads better and avoids the overflow.

b) If (a) is awkward, replace `DotsLoader` with React Native's `ActivityIndicator` inline next to the text — small, gray, no animation hassle.

c) Last resort: just append a static "…" to the text and skip the animation entirely.

Go with (a). The existing `DotsLoader` animation logic can stay as-is — just put it inside its own `<ChatBubble side="agent">` container rendered right after the text bubble. Make the dot bubble visually smaller (less horizontal padding) so it reads as a separate "still thinking" indicator, not a regular message.

Apply to all three event types: `searching`, `ranking`, `booking`. The text bubble + dot bubble together.

---

Don't touch:
- The mock agent logic in `lib/agent/mockAgent.ts` (it works, I just changed it)
- The Zustand stores in `lib/stores/` (just fixed them)
- The booking detail timeline / Mark-as-completed button (working)
- `app.json` branding (done)
- `app-example/` (Expo scaffold, ignore it)

Done when:
- Tap the new chat button → confirm dialog → chat resets cleanly, no stuck `isProcessing`
- Booking detail header sits *below* the status bar on Android, looks clean on iOS too
- "Looking for…", "Found N nearby…", and "Booking the … slot" bubbles render with their text bubble + a separate small typing-indicator bubble below, no overflow, dots stay animated
- `npx tsc --noEmit` and `npx expo lint` both clean
