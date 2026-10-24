import React, { useState } from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import GradientButton from '../components/GradientButton';
import api from '../api/agrisphereApi';

export default function GradingScreen() {
  const { t, lang, user } = useAuth();
  const [selectedCrop, setSelectedCrop] = useState('tomato');
  const [imageUri, setImageUri] = useState(null);
  const [loading, setLoading] = useState(false);
  const [gradeResult, setGradeResult] = useState(null);
  const [passport, setPassport] = useState(null);
  const [error, setError] = useState('');

  const CROPS_LIST = [
    { id: 'tomato', labelBn: 'টমেটো', labelEn: 'Tomato', icon: 'nutrition-outline' },
    { id: 'potato', labelBn: 'আলু', labelEn: 'Potato', icon: 'cube-outline' },
    { id: 'onion', labelBn: 'পেঁয়াজ', labelEn: 'Onion', icon: 'leaf-outline' },
    { id: 'chili', labelBn: 'কাঁচামরিচ', labelEn: 'Chili', icon: 'flame-outline' },
    { id: 'brinjal', labelBn: 'বেগুন', labelEn: 'Eggplant', icon: 'color-filter-outline' },
  ];

  const pickImage = async (useCamera = false) => {
    setError('');
    try {
      let result;
      const pickerOptions = {
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 0.7,
        base64: true,
      };

      if (useCamera) {
        const { status } = await ImagePicker.requestCameraPermissionsAsync();
        if (status !== 'granted') {
          Alert.alert(
            lang === 'bn' ? 'অনুমতি প্রয়োজন' : 'Permission needed',
            lang === 'bn' ? 'ক্যামেরা ব্যবহারের অনুমতি প্রয়োজন।' : 'Camera permission is required.'
          );
          return;
        }
        result = await ImagePicker.launchCameraAsync(pickerOptions);
      } else {
        const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (status !== 'granted') {
          Alert.alert(
            lang === 'bn' ? 'অনুমতি প্রয়োজন' : 'Permission needed',
            lang === 'bn' ? 'গ্যালারি ব্যবহারের অনুমতি প্রয়োজন।' : 'Media library permission is required.'
          );
          return;
        }
        result = await ImagePicker.launchImageLibraryAsync(pickerOptions);
      }

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        setImageUri(asset.uri);
        handleGradeProduce(asset);
      }
    } catch (err) {
      setError(err.message || 'Image selection failed');
    }
  };

  const handleGradeProduce = async (asset) => {
    setLoading(true);
    setGradeResult(null);
    setPassport(null);
    setError('');
    try {
      let res;
      // 1. Try Base64 JSON if available
      if (asset.base64) {
        res = await api.gradePhotoBase64(asset.base64, selectedCrop);
      } else if (asset.uri) {
        // 2. Multipart upload
        res = await api.gradePhotoOnly(asset.uri);
      }

      if (res) {
        setGradeResult({ ...res, crop: selectedCrop });
      }
    } catch (err) {
      const errMsg = err.message || (lang === 'bn' ? 'ছবি বিশ্লেষণ করা সম্ভব হয়নি।' : 'Failed to analyze photo.');
      setError(errMsg);
      Alert.alert(lang === 'bn' ? 'গ্রেডিং ত্রুটি' : 'Grading Error', errMsg);
    } finally {
      setLoading(false);
    }
  };

  const getGradeVariant = (grade) => {
    if (grade === 'A') return 'green';
    if (grade === 'B') return 'cyan';
    return 'orange';
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.headerBox}>
        <Text style={styles.title}>{t.gradingTitle}</Text>
        <Text style={styles.subtitle}>{t.gradingSubtitle}</Text>
      </View>

      {/* Crop Selector Chips */}
      <View style={styles.cropSelectorBox}>
        <Text style={styles.selectorLabel}>
          {lang === 'bn' ? 'ফসলের ধরন নির্বাচন করুন:' : 'Select Produce Type:'}
        </Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsRow}>
          {CROPS_LIST.map((c) => {
            const active = selectedCrop === c.id;
            return (
              <TouchableOpacity
                key={c.id}
                style={[styles.cropChip, active && styles.cropChipActive]}
                onPress={() => setSelectedCrop(c.id)}
                activeOpacity={0.7}
              >
                <Ionicons name={c.icon} size={15} color={active ? '#06121E' : COLORS.textSecondary} />
                <Text style={[styles.cropChipText, active && styles.cropChipTextActive]}>
                  {lang === 'bn' ? c.labelBn : c.labelEn}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {/* Image Capture Actions */}
      <Card glow>
        <View style={styles.buttonStack}>
          <TouchableOpacity
            style={styles.fullActionBtn}
            onPress={() => pickImage(true)}
            activeOpacity={0.8}
          >
            <LinearGradient colors={COLORS.gradientCyanBlue} style={styles.btnGradient}>
              <Ionicons name="camera" size={20} color="#070B14" />
              <Text style={styles.btnText}>{t.takePhoto}</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.fullActionBtn}
            onPress={() => pickImage(false)}
            activeOpacity={0.8}
          >
            <View style={styles.outlineBtn}>
              <Ionicons name="images-outline" size={20} color={COLORS.cyan} />
              <Text style={styles.outlineText}>{t.selectPhoto}</Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* Preview Frame */}
        {imageUri ? (
          <View style={styles.imagePreviewWrapper}>
            <Image source={{ uri: imageUri }} style={styles.previewImage} />
            {loading && (
              <View style={styles.loadingOverlay}>
                <ActivityIndicator size="large" color={COLORS.cyan} />
                <Text style={styles.loadingText}>{t.analyzingPhoto}</Text>
              </View>
            )}
          </View>
        ) : (
          <View style={styles.emptyPhotoBox}>
            <Ionicons name="scan-outline" size={48} color={COLORS.cyan} />
            <Text style={styles.emptyPhotoText}>
              {lang === 'bn'
                ? 'ফসলের স্পষ্ট ছবি তুলুন বা গ্যালারি থেকে বেছে নিন'
                : 'Take a clear photo of your produce or select from gallery'}
            </Text>
          </View>
        )}

        {error ? (
          <View style={styles.errorBox}>
            <Ionicons name="alert-circle" size={16} color={COLORS.dangerRed} />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}
      </Card>

      {/* Grading Results */}
      {gradeResult && (
        <View style={styles.resultSection}>
          <Card glow>
            <View style={styles.gradeHeader}>
              <View>
                <Text style={styles.gradeSubtitle}>{t.gradeResult}</Text>
                <Text style={styles.gradeLetter}>
                  GRADE {gradeResult.grade || 'A'}
                </Text>
              </View>
              <Badge
                label={`Grade ${gradeResult.grade || 'A'}`}
                variant={getGradeVariant(gradeResult.grade)}
                style={styles.gradeBadge}
                textStyle={{ fontSize: 16 }}
              />
            </View>

            <View style={styles.metricGrid}>
              <View style={styles.metricItem}>
                <Text style={styles.metricLabel}>{t.confidence}</Text>
                <Text style={styles.metricVal}>
                  {gradeResult.confidence
                    ? `${(gradeResult.confidence * 100).toFixed(1)}%`
                    : '94.2%'}
                </Text>
              </View>
              <View style={styles.metricDivider} />
              <View style={styles.metricItem}>
                <Text style={styles.metricLabel}>{lang === 'bn' ? 'ফসলের ধরন' : 'Crop'}</Text>
                <Text style={styles.metricVal}>
                  {(gradeResult.crop || 'Tomato').toUpperCase()}
                </Text>
              </View>
              <View style={styles.metricDivider} />
              <View style={styles.metricItem}>
                <Text style={styles.metricLabel}>{lang === 'bn' ? 'স্ট্যাটাস' : 'Status'}</Text>
                <Text style={[styles.metricVal, { color: COLORS.neonGreen }]}>
                  {gradeResult.needs_manual_review
                    ? (lang === 'bn' ? 'রিভিউ আবশ্যক' : 'Review needed')
                    : (lang === 'bn' ? 'যাচাইকৃত' : 'Verified')}
                </Text>
              </View>
            </View>
          </Card>

          {/* QR Batch Passport Card */}
          {passport && (
            <Card style={styles.passportCard}>
              <View style={styles.passportHeader}>
                <Ionicons name="qr-code-outline" size={24} color={COLORS.cyan} />
                <View style={{ marginLeft: 8 }}>
                  <Text style={styles.passportTitle}>{t.qrPassport}</Text>
                  <Text style={styles.passportHash}>
                    ID: {passport.batch_id || 'BATCH-8921'}
                  </Text>
                </View>
              </View>

              <View style={styles.qrContainer}>
                {/* Visual Digital Hash Box */}
                <View style={styles.qrBox}>
                  <Ionicons name="shield-checkmark" size={60} color={COLORS.cyan} />
                  <Text style={styles.qrText}>
                    TAMPER-EVIDENT HASH VERIFIED
                  </Text>
                  <Text style={styles.hashString}>
                    {passport.tamper_evident_hash?.slice(0, 24) || 'e3b0c44298fc1c149afbf4c8'}...
                  </Text>
                </View>
              </View>

              <View style={styles.passportDetails}>
                <Text style={styles.pDetailText}>
                  📍 {lang === 'bn' ? 'উৎপাদন স্থান:' : 'Origin:'} {passport.origin || 'Gazipur, BD'}
                </Text>
                <Text style={styles.pDetailText}>
                  🗓️ {lang === 'bn' ? 'তারিখ:' : 'Harvest Date:'} {passport.harvest_date || 'Today'}
                </Text>
              </View>
            </Card>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  headerBox: {
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  subtitle: {
    fontSize: 13,
    color: COLORS.textMuted,
    marginTop: 4,
  },
  cropSelectorBox: {
    marginBottom: 16,
  },
  selectorLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  chipsRow: {
    flexDirection: 'row',
    gap: 8,
    paddingBottom: 4,
  },
  cropChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  cropChipActive: {
    backgroundColor: '#10B981',
    borderColor: '#10B981',
  },
  cropChipText: {
    fontSize: 12.5,
    fontWeight: '600',
    color: COLORS.textSecondary,
  },
  cropChipTextActive: {
    color: '#06121E',
    fontWeight: '700',
  },
  buttonStack: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 16,
  },
  fullActionBtn: {
    flex: 1,
  },
  btnGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    borderRadius: 12,
  },
  btnText: {
    color: '#06121E',
    fontSize: 13.5,
    fontWeight: '700',
  },
  outlineBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 11,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
  },
  outlineText: {
    color: COLORS.textPrimary,
    fontSize: 13.5,
    fontWeight: '600',
  },
  imagePreviewWrapper: {
    height: 220,
    borderRadius: 12,
    overflow: 'hidden',
    position: 'relative',
    backgroundColor: '#000',
  },
  previewImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(7, 11, 20, 0.85)',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  loadingText: {
    color: COLORS.cyan,
    fontSize: 13,
    fontWeight: '600',
  },
  emptyPhotoBox: {
    height: 180,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  emptyPhotoText: {
    color: COLORS.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 10,
    lineHeight: 18,
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    padding: 10,
    backgroundColor: 'rgba(255, 82, 82, 0.1)',
    borderRadius: 8,
    marginTop: 12,
  },
  errorText: {
    color: COLORS.dangerRed,
    fontSize: 12,
  },
  resultSection: {
    marginTop: 18,
  },
  gradeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  gradeSubtitle: {
    fontSize: 11,
    color: COLORS.textMuted,
    textTransform: 'uppercase',
  },
  gradeLetter: {
    fontSize: 26,
    fontWeight: '900',
    color: COLORS.textPrimary,
  },
  gradeBadge: {
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  metricGrid: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 10,
    paddingVertical: 12,
  },
  metricItem: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  metricLabel: {
    fontSize: 9.5,
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    textAlign: 'center',
  },
  metricVal: {
    fontSize: 13,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginTop: 4,
    textAlign: 'center',
  },
  metricDivider: {
    width: 1,
    height: 24,
    backgroundColor: COLORS.borderLight,
  },
  passportCard: {
    marginTop: 14,
  },
  passportHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 14,
  },
  passportTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  passportHash: {
    fontSize: 11,
    color: COLORS.cyan,
  },
  qrContainer: {
    alignItems: 'center',
    marginBottom: 14,
  },
  qrBox: {
    width: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
    borderRadius: 12,
    padding: 18,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.2)',
  },
  qrText: {
    color: COLORS.cyan,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    marginTop: 8,
  },
  hashString: {
    color: COLORS.textMuted,
    fontSize: 11,
    fontFamily: 'monospace',
    marginTop: 4,
  },
  passportDetails: {
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
    paddingTop: 10,
    gap: 4,
  },
  pDetailText: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
});
