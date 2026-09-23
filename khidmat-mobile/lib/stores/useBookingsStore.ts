import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { ServiceCategory } from '../mock/providers';
import type { AgentEvent } from '../agent/types';

export type Booking = {
  id: string;
  providerId: string;
  providerName: string;
  category: ServiceCategory;
  sector: string;
  scheduledFor: string; // 'Tomorrow, 10:00 AM'
  scheduledTimestamp: number;
  status: 'confirmed' | 'reminded' | 'completed' | 'cancelled';
  reminderAt: string;
  agentThread: AgentEvent[]; // preserved events from the conversation
  createdAt: number;
};

type BookingsState = {
  bookings: Booking[];
  addBooking: (booking: Booking) => void;
  updateStatus: (
    id: string,
    status: 'confirmed' | 'reminded' | 'completed' | 'cancelled',
  ) => void;
  cancel: (id: string) => void;
  clear: () => void;
};

export const useBookingsStore = create<BookingsState>()(
  persist(
    (set) => ({
      bookings: [],
      addBooking: (booking: Booking) =>
        set((state) => ({ bookings: [booking, ...state.bookings] })),
      updateStatus: (id, status) =>
        set((state) => ({
          bookings: state.bookings.map((b) =>
            b.id === id ? { ...b, status } : b,
          ),
        })),
      cancel: (id) =>
        set((state) => ({
          bookings: state.bookings.map((b) =>
            b.id === id ? { ...b, status: 'cancelled' as const } : b,
          ),
        })),
      clear: () => set({ bookings: [] }),
    }),
    {
      name: 'khidmat-bookings',
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
