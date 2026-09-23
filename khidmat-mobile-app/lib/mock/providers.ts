export type ServiceCategory =
  | 'ac'
  | 'plumber'
  | 'electrician'
  | 'tutor'
  | 'beautician';

export type Provider = {
  id: string;
  name: string;
  category: ServiceCategory;
  sector: string;
  coords: { lat: number; lng: number };
  rating: number;
  reviewCount: number;
  yearsExperience: number;
  priceRange: string;
  phone: string;
  availableSlots: string[];
};

/** Sector center coordinates for Islamabad */
export const SECTOR_COORDS: Record<string, { lat: number; lng: number }> = {
  'F-6': { lat: 33.7295, lng: 73.0775 },
  'F-7': { lat: 33.717, lng: 73.0707 },
  'F-8/1': { lat: 33.7055, lng: 73.0525 },
  'F-8/2': { lat: 33.704, lng: 73.049 },
  'F-10/1': { lat: 33.6945, lng: 73.018 },
  'F-10/3': { lat: 33.6938, lng: 73.0162 },
  'F-11/1': { lat: 33.685, lng: 73.007 },
  'F-11/3': { lat: 33.684, lng: 73.004 },
  'G-9': { lat: 33.68, lng: 72.987 },
  'G-10': { lat: 33.684, lng: 72.982 },
  'G-11': { lat: 33.662, lng: 72.976 },
  'G-13': { lat: 33.647, lng: 72.951 },
  'I-8/3': { lat: 33.662, lng: 73.079 },
  'I-9': { lat: 33.652, lng: 73.07 },
};

export const providers: Provider[] = [
  // ── AC (3) ──────────────────────────────────────────
  {
    id: 'p001',
    name: 'Ali AC Services',
    category: 'ac',
    sector: 'G-13',
    coords: { lat: 33.648, lng: 72.952 },
    rating: 4.7,
    reviewCount: 124,
    yearsExperience: 8,
    priceRange: 'PKR 1500-3000',
    phone: '+92-300-1234567',
    availableSlots: ['10:00 AM', '2:00 PM', '6:00 PM'],
  },
  {
    id: 'p002',
    name: 'CoolFix Islamabad',
    category: 'ac',
    sector: 'F-10/3',
    coords: { lat: 33.694, lng: 73.017 },
    rating: 4.5,
    reviewCount: 89,
    yearsExperience: 5,
    priceRange: 'PKR 2000-4000',
    phone: '+92-301-2345678',
    availableSlots: ['11:00 AM', '3:00 PM'],
  },
  {
    id: 'p003',
    name: 'Khan Cooling Solutions',
    category: 'ac',
    sector: 'I-8/3',
    coords: { lat: 33.663, lng: 73.08 },
    rating: 4.3,
    reviewCount: 56,
    yearsExperience: 3,
    priceRange: 'PKR 1000-2500',
    phone: '+92-302-3456789',
    availableSlots: ['9:00 AM', '1:00 PM', '5:00 PM'],
  },

  // ── Plumber (3) ─────────────────────────────────────
  {
    id: 'p004',
    name: 'Sajid Plumbing',
    category: 'plumber',
    sector: 'F-7',
    coords: { lat: 33.718, lng: 73.071 },
    rating: 4.6,
    reviewCount: 201,
    yearsExperience: 12,
    priceRange: 'PKR 800-2000',
    phone: '+92-303-4567890',
    availableSlots: ['10:00 AM', '2:00 PM', '4:00 PM'],
  },
  {
    id: 'p005',
    name: 'QuickFix Plumbers',
    category: 'plumber',
    sector: 'G-9',
    coords: { lat: 33.681, lng: 72.988 },
    rating: 4.4,
    reviewCount: 78,
    yearsExperience: 6,
    priceRange: 'PKR 1000-2500',
    phone: '+92-304-5678901',
    availableSlots: ['9:00 AM', '12:00 PM', '3:00 PM'],
  },
  {
    id: 'p006',
    name: 'Ahsan Sanitary Works',
    category: 'plumber',
    sector: 'F-11/1',
    coords: { lat: 33.686, lng: 73.008 },
    rating: 4.2,
    reviewCount: 43,
    yearsExperience: 4,
    priceRange: 'PKR 700-1800',
    phone: '+92-305-6789012',
    availableSlots: ['11:00 AM', '1:00 PM', '5:00 PM'],
  },

  // ── Electrician (3) ─────────────────────────────────
  {
    id: 'p007',
    name: 'Bilal Electric Works',
    category: 'electrician',
    sector: 'G-10',
    coords: { lat: 33.685, lng: 72.983 },
    rating: 4.8,
    reviewCount: 167,
    yearsExperience: 10,
    priceRange: 'PKR 1000-3000',
    phone: '+92-306-7890123',
    availableSlots: ['10:00 AM', '2:00 PM', '6:00 PM'],
  },
  {
    id: 'p008',
    name: 'PowerPro Services',
    category: 'electrician',
    sector: 'F-6',
    coords: { lat: 33.73, lng: 73.078 },
    rating: 4.5,
    reviewCount: 92,
    yearsExperience: 7,
    priceRange: 'PKR 1200-3500',
    phone: '+92-307-8901234',
    availableSlots: ['9:00 AM', '11:00 AM', '4:00 PM'],
  },
  {
    id: 'p009',
    name: 'Faisal Electricals',
    category: 'electrician',
    sector: 'I-9',
    coords: { lat: 33.653, lng: 73.071 },
    rating: 4.1,
    reviewCount: 35,
    yearsExperience: 3,
    priceRange: 'PKR 800-2000',
    phone: '+92-308-9012345',
    availableSlots: ['10:00 AM', '3:00 PM'],
  },

  // ── Tutor (3) ───────────────────────────────────────
  {
    id: 'p010',
    name: 'Ayesha Math Academy',
    category: 'tutor',
    sector: 'F-10/1',
    coords: { lat: 33.695, lng: 73.019 },
    rating: 4.9,
    reviewCount: 214,
    yearsExperience: 15,
    priceRange: 'PKR 3000-6000/mo',
    phone: '+92-309-0123456',
    availableSlots: ['10:00 AM', '2:00 PM', '5:00 PM'],
  },
  {
    id: 'p011',
    name: 'Hammad Tutors',
    category: 'tutor',
    sector: 'G-11',
    coords: { lat: 33.663, lng: 72.977 },
    rating: 4.6,
    reviewCount: 98,
    yearsExperience: 8,
    priceRange: 'PKR 2500-5000/mo',
    phone: '+92-310-1234567',
    availableSlots: ['9:00 AM', '1:00 PM', '4:00 PM'],
  },
  {
    id: 'p012',
    name: 'STEM Bright Tutors',
    category: 'tutor',
    sector: 'F-8/1',
    coords: { lat: 33.706, lng: 73.053 },
    rating: 4.4,
    reviewCount: 62,
    yearsExperience: 5,
    priceRange: 'PKR 2000-4500/mo',
    phone: '+92-311-2345678',
    availableSlots: ['11:00 AM', '3:00 PM', '6:00 PM'],
  },

  // ── Beautician (3) ─────────────────────────────────
  {
    id: 'p013',
    name: 'Maria Beauty Salon',
    category: 'beautician',
    sector: 'F-7',
    coords: { lat: 33.716, lng: 73.069 },
    rating: 4.7,
    reviewCount: 189,
    yearsExperience: 9,
    priceRange: 'PKR 2000-5000',
    phone: '+92-312-3456789',
    availableSlots: ['10:00 AM', '1:00 PM', '4:00 PM'],
  },
  {
    id: 'p014',
    name: 'Glow Home Service',
    category: 'beautician',
    sector: 'G-10',
    coords: { lat: 33.683, lng: 72.981 },
    rating: 4.5,
    reviewCount: 134,
    yearsExperience: 6,
    priceRange: 'PKR 1500-4000',
    phone: '+92-313-4567890',
    availableSlots: ['9:00 AM', '12:00 PM', '3:00 PM'],
  },
  {
    id: 'p015',
    name: 'Saima at-Home Beauty',
    category: 'beautician',
    sector: 'F-11/3',
    coords: { lat: 33.683, lng: 73.003 },
    rating: 4.3,
    reviewCount: 47,
    yearsExperience: 4,
    priceRange: 'PKR 1200-3500',
    phone: '+92-314-5678901',
    availableSlots: ['11:00 AM', '2:00 PM', '5:00 PM'],
  },
];
