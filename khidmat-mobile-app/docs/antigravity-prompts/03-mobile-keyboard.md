Hey — found a tab bar overlap issue on Android (icons getting overlaid by the system nav buttons after backgrounding the app and coming back). Fixed it in `app/(tabs)/_layout.tsx` by reading `useSafeAreaInsets()` from `react-native-safe-area-context` and padding the tab bar by `insets.bottom`. Works now.

One more thing left for you:

**Keyboard covers the chat input on Android**

Tap the chat input on the Chat screen, keyboard slides up, keyboard renders *on top of* the input bar. Can't see what you're typing.

`app/(tabs)/index.tsx` has a `KeyboardAvoidingView` wrapping the chat body, but the behavior prop is:

```tsx
behavior={Platform.OS === 'ios' ? 'padding' : undefined}
```

`undefined` on Android means the component does nothing. That's the bug.

Fix approach — try in order, escalate only if needed:

**1. First try the cheap fix.** In `app/(tabs)/index.tsx`:
- Change `behavior` to `'padding'` for both platforms (or `'height'` on Android — try both, pick whichever feels less janky).
- Set `keyboardVerticalOffset` properly. Right now it's `0`. With the tab bar present below the screen, it likely needs to be roughly the tab bar height (60 + bottom safe-area inset). Read `useSafeAreaInsets()` in this component to compute it.

In `app/(tabs)/_layout.tsx`:
- Add `tabBarHideOnKeyboard: true` to the `Tabs` `screenOptions`. The tab bar should tuck away when the keyboard is open — gives the chat thread more breathing room and avoids fighting the KAV math.

Test on a real Android device with edge-to-edge enabled (which we have in `app.json`). Pixel emulators sometimes lie about keyboard behavior.

**2. If (1) still misbehaves** on Android — KAV is known to be unreliable with edge-to-edge mode in SDK 54 — swap to `react-native-keyboard-controller`. It's the community-standard library for keyboard handling now. Install it:

```
npx expo install react-native-keyboard-controller
```

Then replace the RN core `KeyboardAvoidingView` in `app/(tabs)/index.tsx` with the one from `react-native-keyboard-controller`, and add `<KeyboardProvider>` near the top of `app/_layout.tsx` (above the `<Stack>`) per the library's docs. Don't add the library unless step 1 actually fails — keep dependencies tight.

Don't touch:
- The tab bar safe-area inset fix in `app/(tabs)/_layout.tsx` (I just did it).
- The Settings sector input (different screen, handled by its own ScrollView's `keyboardShouldPersistTaps`).
- The booking detail screen (no text inputs).
- Anything else.

Done when:
- Tap chat input on Android → keyboard opens → input bar sits visibly above the keyboard → you can see what you're typing.
- iOS still works (don't regress).
- Tab bar disappears while typing and reappears when keyboard dismisses.
- Sending a message still works (focus, scroll, haptic).
- `npx tsc --noEmit` and `npx expo lint` both clean.
