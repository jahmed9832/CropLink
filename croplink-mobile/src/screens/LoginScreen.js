import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import GradientButton from '../components/GradientButton';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { LOCAL_SERVER_URL, RENDER_SERVER_URL } from '../api/agrisphereApi';
import { Alert } from 'react-native';

const DISTRICTS = ['Dhaka', 'Gazipur', 'Bogura', 'Chattogram', 'Rajshahi', 'Khulna', 'Rangpur', 'Mymensingh', 'Dinajpur'];

export default function LoginScreen() {
  const { login, register, t, lang, toggleLanguage, serverStatus, serverUrl, switchServerUrl, refreshServerStatus } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('farmer');
  const [district, setDistrict] = useState('Gazipur');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setError('');
    if (!phone || !password) {
      setError(lang === 'bn' ? 'ফোন নম্বর ও পাসওয়ার্ড দিন' : 'Please enter phone and password');
      return;
    }

    setLoading(true);
    try {
      if (isRegister) {
        await register({ name: name || 'User', phone, password, role, district });
      } else {
        await login(phone, password);
      }
    } catch (err) {
      setError(err.message || (lang === 'bn' ? 'লগইন ব্যর্থ হয়েছে। আবার চেষ্টা করুন।' : 'Login failed. Try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleDemoFill = (demoRole) => {
    if (demoRole === 'farmer') {
      setPhone('01700000001');
      setPassword('demo1234');
      setRole('farmer');
    } else {
      setPhone('01700000002');
      setPassword('demo1234');
      setRole('buyer');
    }
    setIsRegister(false);
    setError('');
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        {/* Top Header with Lang Toggle & Server Pill */}
        <View style={styles.topBar}>
          <TouchableOpacity
            onPress={() => {
              Alert.alert(
                lang === 'bn' ? 'সার্ভার সংযোগ' : 'Server Connection',
                `${lang === 'bn' ? 'বর্তমান:' : 'Current:'}\n${serverUrl}\n\n${lang === 'bn' ? 'কোন সার্ভার ব্যবহার করতে চান?' : 'Select server:'}`,
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
            }}
            style={styles.serverPill}
          >
            <View
              style={[
                styles.dot,
                {
                  backgroundColor:
                    serverStatus === 'active'
                      ? COLORS.neonGreen
                      : serverStatus === 'offline'
                      ? COLORS.dangerRed
                      : COLORS.warningOrange,
                },
              ]}
            />
            <Text style={styles.serverText}>
              {serverStatus === 'active'
                ? t.serverActive
                : serverStatus === 'offline'
                ? t.serverOffline
                : t.serverWaking} • {serverUrl && serverUrl.includes('192.168') ? 'Local' : 'Cloud'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={toggleLanguage} style={styles.langBtn}>
            <Text style={styles.langText}>{lang === 'bn' ? 'English' : 'বাংলা'}</Text>
          </TouchableOpacity>
        </View>

        {/* Hero Branding */}
        <View style={styles.heroSection}>
          <LinearGradient
            colors={COLORS.gradientCyanBlue}
            style={styles.logoCircle}
          >
            <Ionicons name="leaf" size={32} color="#070B14" />
          </LinearGradient>
          <Text style={styles.brandTitle}>CropLink</Text>
          <Text style={styles.brandTagline}>{t.tagline}</Text>
        </View>

        {/* Auth Box */}
        <Card glow style={styles.authCard}>
          {/* Tab Switcher */}
          <View style={styles.tabRow}>
            <TouchableOpacity
              onPress={() => { setIsRegister(false); setError(''); }}
              style={[styles.tabBtn, !isRegister && styles.tabBtnActive]}
            >
              <Text style={[styles.tabText, !isRegister && styles.tabTextActive]}>{t.login}</Text>
            </TouchableOpacity>
            <TouchableOpacity
              onPress={() => { setIsRegister(true); setError(''); }}
              style={[styles.tabBtn, isRegister && styles.tabBtnActive]}
            >
              <Text style={[styles.tabText, isRegister && styles.tabTextActive]}>{t.register}</Text>
            </TouchableOpacity>
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color={COLORS.dangerRed} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          {isRegister && (
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>{lang === 'bn' ? 'আপনার নাম' : 'Full Name'}</Text>
              <TextInput
                style={styles.input}
                placeholder={lang === 'bn' ? 'করিম মিয়া' : 'Rahim Ahmed'}
                placeholderTextColor={COLORS.textMuted}
                value={name}
                onChangeText={setName}
              />
            </View>
          )}

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>{t.phone}</Text>
            <TextInput
              style={styles.input}
              placeholder={t.phonePlaceholder}
              placeholderTextColor={COLORS.textMuted}
              keyboardType="phone-pad"
              value={phone}
              onChangeText={setPhone}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>{t.password}</Text>
            <TextInput
              style={styles.input}
              placeholder={t.passwordPlaceholder}
              placeholderTextColor={COLORS.textMuted}
              secureTextEntry
              value={password}
              onChangeText={setPassword}
            />
          </View>

          {isRegister && (
            <>
              {/* Role Selector */}
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>{t.role}</Text>
                <View style={styles.roleRow}>
                  <TouchableOpacity
                    onPress={() => setRole('farmer')}
                    style={[styles.roleBtn, role === 'farmer' && styles.roleBtnActive]}
                  >
                    <Ionicons
                      name="person"
                      size={16}
                      color={role === 'farmer' ? COLORS.cyan : COLORS.textMuted}
                    />
                    <Text
                      style={[styles.roleText, role === 'farmer' && styles.roleTextActive]}
                    >
                      {t.farmer}
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    onPress={() => setRole('buyer')}
                    style={[styles.roleBtn, role === 'buyer' && styles.roleBtnActive]}
                  >
                    <Ionicons
                      name="business"
                      size={16}
                      color={role === 'buyer' ? COLORS.cyan : COLORS.textMuted}
                    />
                    <Text
                      style={[styles.roleText, role === 'buyer' && styles.roleTextActive]}
                    >
                      {t.buyer}
                    </Text>
                  </TouchableOpacity>
                </View>
              </View>

              {/* District Selector */}
              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>{t.district}</Text>
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.districtScroll}>
                  {DISTRICTS.map((d) => (
                    <TouchableOpacity
                      key={d}
                      onPress={() => setDistrict(d)}
                      style={[styles.districtChip, district === d && styles.districtChipActive]}
                    >
                      <Text
                        style={[
                          styles.districtText,
                          district === d && styles.districtTextActive,
                        ]}
                      >
                        {d}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            </>
          )}

          <GradientButton
            title={loading ? t.loading : isRegister ? t.register : t.login}
            onPress={handleSubmit}
            loading={loading}
            style={styles.submitBtn}
          />

          {/* 1-Click Demo Login for quick testing */}
          <View style={styles.demoSection}>
            <Text style={styles.demoTitle}>
              {lang === 'bn' ? '⚡ দ্রুত পরীক্ষার জন্য ডেমো একাউন্ট:' : '⚡ 1-Click Demo Quick Sign In:'}
            </Text>
            <View style={styles.demoBtnRow}>
              <TouchableOpacity
                onPress={() => handleDemoFill('farmer')}
                style={styles.demoBtn}
              >
                <Text style={styles.demoBtnText}>🌾 {t.farmer} (Demo)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => handleDemoFill('buyer')}
                style={styles.demoBtn}
              >
                <Text style={styles.demoBtnText}>🏢 {t.buyer} (Demo)</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
  },
  scrollContent: {
    padding: 20,
    paddingTop: 45,
    paddingBottom: 40,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  serverPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  serverText: {
    color: COLORS.textSecondary,
    fontSize: 11,
    fontWeight: '600',
  },
  langBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 242, 254, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.3)',
  },
  langText: {
    color: COLORS.cyan,
    fontSize: 12,
    fontWeight: '700',
  },
  heroSection: {
    alignItems: 'center',
    marginBottom: 24,
  },
  logoCircle: {
    width: 64,
    height: 64,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    shadowColor: '#00F2FE',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 8,
  },
  brandTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: COLORS.textPrimary,
    letterSpacing: 0.5,
  },
  brandTagline: {
    fontSize: 13,
    color: COLORS.textSecondary,
    textAlign: 'center',
    marginTop: 4,
  },
  authCard: {
    padding: 20,
  },
  tabRow: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 10,
    padding: 3,
    marginBottom: 20,
  },
  tabBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 8,
  },
  tabBtnActive: {
    backgroundColor: COLORS.bgCardHover,
  },
  tabText: {
    color: COLORS.textMuted,
    fontSize: 14,
    fontWeight: '600',
  },
  tabTextActive: {
    color: COLORS.cyan,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(255, 82, 82, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255, 82, 82, 0.3)',
    borderRadius: 8,
    padding: 10,
    marginBottom: 16,
  },
  errorText: {
    color: COLORS.dangerRed,
    fontSize: 12,
    flex: 1,
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    color: COLORS.textSecondary,
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 6,
  },
  input: {
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: COLORS.textPrimary,
    fontSize: 14,
  },
  roleRow: {
    flexDirection: 'row',
    gap: 10,
  },
  roleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  roleBtnActive: {
    borderColor: COLORS.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.08)',
  },
  roleText: {
    color: COLORS.textMuted,
    fontSize: 13,
    fontWeight: '600',
  },
  roleTextActive: {
    color: COLORS.cyan,
  },
  districtScroll: {
    flexDirection: 'row',
  },
  districtChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    marginRight: 8,
  },
  districtChipActive: {
    borderColor: COLORS.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.15)',
  },
  districtText: {
    color: COLORS.textSecondary,
    fontSize: 12,
  },
  districtTextActive: {
    color: COLORS.cyan,
    fontWeight: '700',
  },
  submitBtn: {
    marginTop: 8,
    marginBottom: 18,
  },
  demoSection: {
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
    paddingTop: 16,
  },
  demoTitle: {
    color: COLORS.textMuted,
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 8,
  },
  demoBtnRow: {
    flexDirection: 'row',
    gap: 10,
  },
  demoBtn: {
    flex: 1,
    backgroundColor: 'rgba(0, 242, 254, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.2)',
    paddingVertical: 9,
    borderRadius: 8,
    alignItems: 'center',
  },
  demoBtnText: {
    color: COLORS.cyan,
    fontSize: 12,
    fontWeight: '600',
  },
});
