import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../constants/theme';

export default function Badge({ label, variant = 'cyan', style, textStyle, showDot = true }) {
  const getColors = () => {
    switch (variant) {
      case 'success':
      case 'green':
        return { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.28)', dot: '#10B981' };
      case 'warning':
      case 'orange':
        return { bg: 'rgba(245, 158, 11, 0.12)', text: '#F59E0B', border: 'rgba(245, 158, 11, 0.28)', dot: '#F59E0B' };
      case 'danger':
      case 'red':
        return { bg: 'rgba(239, 68, 68, 0.12)', text: '#EF4444', border: 'rgba(239, 68, 68, 0.28)', dot: '#EF4444' };
      case 'purple':
        return { bg: 'rgba(139, 92, 246, 0.12)', text: '#8B5CF6', border: 'rgba(139, 92, 246, 0.28)', dot: '#8B5CF6' };
      case 'cyan':
      default:
        return { bg: 'rgba(14, 165, 233, 0.12)', text: '#38BDF8', border: 'rgba(14, 165, 233, 0.28)', dot: '#38BDF8' };
    }
  };

  const c = getColors();

  return (
    <View style={[styles.badge, { backgroundColor: c.bg, borderColor: c.border }, style]}>
      {showDot && <View style={[styles.dot, { backgroundColor: c.dot }]} />}
      <Text style={[styles.text, { color: c.text }, textStyle]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4.5,
    borderRadius: 20,
    borderWidth: 1,
    alignSelf: 'flex-start',
    gap: 5,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  text: {
    fontSize: 11.5,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
});
