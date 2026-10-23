import React from 'react';
import { View, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { COLORS, SHADOWS } from '../constants/theme';

export default function Card({ children, style, glow = false }) {
  if (glow) {
    return (
      <View style={[styles.glowWrapper, style]}>
        <LinearGradient
          colors={['rgba(16, 185, 129, 0.28)', 'rgba(56, 189, 248, 0.08)']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.glowGradientBorder}
        >
          <View style={styles.glowInner}>{children}</View>
        </LinearGradient>
      </View>
    );
  }

  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    marginBottom: 14,
    ...SHADOWS.card,
  },
  glowWrapper: {
    borderRadius: 16,
    marginBottom: 14,
    overflow: 'hidden',
    ...SHADOWS.card,
  },
  glowGradientBorder: {
    padding: 1,
    borderRadius: 16,
  },
  glowInner: {
    backgroundColor: COLORS.bgCardSolid,
    borderRadius: 15,
    padding: 18,
  },
});
