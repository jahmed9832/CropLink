export const COLORS = {
  // Backgrounds - Deep Slate & Graphite Canvas
  bgDark: '#080C15',
  bgCard: 'rgba(16, 24, 40, 0.85)',
  bgCardSolid: '#0F172A',
  bgCardHover: '#172238',
  bgInput: 'rgba(15, 23, 42, 0.95)',
  bgGlass: 'rgba(255, 255, 255, 0.035)',

  // Borders - Hairline refined edges
  borderLight: 'rgba(255, 255, 255, 0.08)',
  borderGlow: 'rgba(16, 185, 129, 0.30)',
  borderAccent: 'rgba(56, 189, 248, 0.25)',

  // Brand / Accents - World-class Agritech & Market colors
  primary: '#10B981',
  primaryLight: '#34D399',
  emerald: '#10B981',
  cyan: '#0EA5E9',
  skyBlue: '#38BDF8',
  electricBlue: '#2563EB',
  neonGreen: '#10B981',
  warningOrange: '#F59E0B',
  dangerRed: '#EF4444',
  purple: '#8B5CF6',
  darkCyan: '#0D9488',

  // Gradients (tuples for expo-linear-gradient)
  gradientCyanBlue: ['#10B981', '#0EA5E9'],
  gradientGreenCyan: ['#059669', '#10B981'],
  gradientPurpleBlue: ['#6366F1', '#38BDF8'],
  gradientDarkCard: ['rgba(22, 33, 56, 0.92)', 'rgba(12, 18, 32, 0.92)'],
  gradientHero: ['#0E1B33', '#080C15'],

  // Text
  textPrimary: '#F8FAFC',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  textCyan: '#38BDF8',
  textEmerald: '#34D399',
};

export const SHADOWS = {
  subtle: {
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
    elevation: 3,
  },
  card: {
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 4,
  },
  glowGreen: {
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 5,
  },
};
