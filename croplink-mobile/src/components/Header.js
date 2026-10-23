import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import { LOCAL_SERVER_URL, RENDER_SERVER_URL } from '../api/agrisphereApi';

export default function Header({ title, showBack = false, onBack, rightElement }) {
  const { lang, toggleLanguage, serverStatus, serverUrl, switchServerUrl, refreshServerStatus, t, user, logout } = useAuth();

  const getStatusInfo = () => {
    if (serverStatus === 'active') {
      return { color: COLORS.neonGreen, text: t.serverActive, icon: 'ellipse' };
    }
    if (serverStatus === 'offline') {
      return { color: COLORS.dangerRed, text: t.serverOffline, icon: 'alert-circle' };
    }
    return { color: COLORS.warningOrange, text: t.serverWaking, icon: 'hourglass-outline' };
  };

  const status = getStatusInfo();

  const handleServerPress = () => {
    const isLocal = serverUrl && serverUrl.includes('192.168');
    Alert.alert(
      lang === 'bn' ? 'সার্ভার সংযোগ' : 'Server Connection',
      `${lang === 'bn' ? 'বর্তমান সার্ভার:' : 'Current:'}\n${serverUrl}\n\n${lang === 'bn' ? 'কোন সার্ভার ব্যবহার করতে চান?' : 'Choose server:'}`,
      [
        {
          text: `💻 ${lang === 'bn' ? 'লোকাল পিসি' : 'Local PC'} (192.168.0.106)`,
          onPress: () => switchServerUrl(LOCAL_SERVER_URL),
        },
        {
          text: `☁️ ${lang === 'bn' ? 'রেন্ডার ক্লাউড' : 'Render Cloud'}`,
          onPress: () => switchServerUrl(RENDER_SERVER_URL),
        },
        { text: t.close || 'Cancel', style: 'cancel' },
      ]
    );
  };

  return (
    <View style={styles.container}>
      {/* Top Bar */}
      <View style={styles.topRow}>
        <View style={styles.brandRow}>
          {showBack ? (
            <TouchableOpacity onPress={onBack} style={styles.iconBtn}>
              <Ionicons name="arrow-back" size={22} color={COLORS.cyan} />
            </TouchableOpacity>
          ) : (
            <View style={styles.logoPill}>
              <Ionicons name="leaf" size={18} color="#070B14" />
            </View>
          )}
          <View style={{ flex: 1, marginRight: 8 }}>
            <Text style={styles.brandTitle} numberOfLines={1} ellipsizeMode="tail">
              {title || 'CropLink'}
            </Text>
            <TouchableOpacity onPress={handleServerPress} activeOpacity={0.7} style={styles.statusRow}>
              <View style={[styles.statusDot, { backgroundColor: status.color }]} />
              <Text style={[styles.statusText, { color: status.color }]}>
                {status.text} • {serverUrl && serverUrl.includes('192.168') ? 'Local' : 'Cloud'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.actionsRow}>
          {/* Language Switcher */}
          <TouchableOpacity onPress={toggleLanguage} style={styles.langBtn} activeOpacity={0.7}>
            <Text style={styles.langText}>{lang === 'bn' ? 'English' : 'বাংলা'}</Text>
          </TouchableOpacity>

          {/* User profile / logout */}
          {user && (
            <TouchableOpacity onPress={logout} style={styles.iconBtn} activeOpacity={0.7}>
              <Ionicons name="log-out-outline" size={20} color={COLORS.textSecondary} />
            </TouchableOpacity>
          )}

          {rightElement}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 14,
    backgroundColor: COLORS.bgDark,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.borderLight,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brandRow: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginRight: 8,
  },
  logoPill: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: COLORS.cyan,
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.textPrimary,
    letterSpacing: 0.5,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 2,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '500',
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  langBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.25)',
  },
  langText: {
    color: COLORS.cyan,
    fontSize: 12,
    fontWeight: '700',
  },
  iconBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: COLORS.bgCardHover,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
