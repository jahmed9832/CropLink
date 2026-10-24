import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import GradientButton from '../components/GradientButton';
import api from '../api/agrisphereApi';

const CROPS = ['tomato', 'potato', 'onion', 'brinjal', 'chili', 'cabbage', 'rice'];
const MARKETS = ['Dhaka', 'Chattogram', 'Rajshahi', 'Bogura', 'Khulna'];
const GRADES = ['A', 'B', 'C'];

export default function DecisionScreen() {
  const { t, lang } = useAuth();
  const [crop, setCrop] = useState('tomato');
  const [quantity, setQuantity] = useState('500');
  const [grade, setGrade] = useState('A');
  const [market, setMarket] = useState('Dhaka');

  // Advanced cost overrides (Proposal feature: farmer can correct inputs)
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [transportCost, setTransportCost] = useState('0.02');
  const [handlingCost, setHandlingCost] = useState('0.5');
  const [storageCost, setStorageCost] = useState('0.3');
  const [spoilageRisk, setSpoilageRisk] = useState('0.035');
  const [costsEdited, setCostsEdited] = useState(false);
  const [spoilageEdited, setSpoilageEdited] = useState(false);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleCalculate = async () => {
    setError('');
    const qtyNum = parseFloat(quantity);
    if (!qtyNum || qtyNum <= 0) {
      setError(lang === 'bn' ? 'সঠিক পরিমাণ (কেজি) দিন' : 'Please enter a valid quantity in kg');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        crop,
        quantity_kg: qtyNum,
        grade,
        market,
      };
      if (costsEdited) {
        payload.costs = {
          transport_per_kg_km: parseFloat(transportCost) || 0.02,
          handling_per_kg: parseFloat(handlingCost) || 0.5,
          storage_per_kg_day: parseFloat(storageCost) || 0.3,
          commission_pct: 2.0,
          local_market_km: 15,
        };
      }
      if (spoilageEdited) {
        payload.spoilage_per_day = parseFloat(spoilageRisk) || 0.035;
      }

      const res = await api.decide(payload);
      setResult(res);
    } catch (err) {
      setError(err.message || (lang === 'bn' ? 'হিসাব সম্পন্ন করা যায়নি।' : 'Calculation failed.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Title */}
      <View style={styles.headerBox}>
        <Text style={styles.title}>{t.decisionTitle}</Text>
        <Text style={styles.subtitle}>{t.decisionSubtitle}</Text>
      </View>

      {/* Input Form Card */}
      <Card glow>
        {/* Crop Selector */}
        <Text style={styles.inputLabel}>{t.crop}</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
          {CROPS.map((c) => (
            <TouchableOpacity
              key={c}
              onPress={() => setCrop(c)}
              style={[styles.chip, crop === c && styles.chipActive]}
            >
              <Text style={[styles.chipText, crop === c && styles.chipTextActive]}>
                {c.toUpperCase()}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Quantity & Grade */}
        <View style={styles.row}>
          <View style={styles.halfCol}>
            <Text style={styles.inputLabel}>{t.quantity}</Text>
            <TextInput
              style={styles.input}
              keyboardType="numeric"
              value={quantity}
              onChangeText={setQuantity}
              placeholder="500"
              placeholderTextColor={COLORS.textMuted}
            />
          </View>

          <View style={styles.halfCol}>
            <Text style={styles.inputLabel}>{t.grade}</Text>
            <View style={styles.gradeRow}>
              {GRADES.map((g) => (
                <TouchableOpacity
                  key={g}
                  onPress={() => setGrade(g)}
                  style={[styles.gradeBtn, grade === g && styles.gradeBtnActive]}
                >
                  <Text style={[styles.gradeText, grade === g && styles.gradeTextActive]}>
                    {g}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        </View>

        {/* Target Market */}
        <Text style={styles.inputLabel}>{t.market}</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll}>
          {MARKETS.map((m) => (
            <TouchableOpacity
              key={m}
              onPress={() => setMarket(m)}
              style={[styles.chip, market === m && styles.chipActive]}
            >
              <Text style={[styles.chipText, market === m && styles.chipTextActive]}>
                {m}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Advanced Cost Adjustments (Accordion) */}
        <TouchableOpacity
          onPress={() => setShowAdvanced(!showAdvanced)}
          style={styles.accordionHeader}
          activeOpacity={0.7}
        >
          <Text style={styles.accordionTitle}>
            ⚙️ {t.adjustCosts} {showAdvanced ? '▲' : '▼'}
          </Text>
        </TouchableOpacity>

        {showAdvanced && (
          <View style={styles.advancedBox}>
            <View style={styles.costItem}>
              <Text style={styles.costLabel}>{t.transportCost}</Text>
              <TextInput
                style={styles.smallInput}
                keyboardType="numeric"
                value={transportCost}
                onChangeText={(val) => { setTransportCost(val); setCostsEdited(true); }}
              />
            </View>
            <View style={styles.costItem}>
              <Text style={styles.costLabel}>{t.handlingCost}</Text>
              <TextInput
                style={styles.smallInput}
                keyboardType="numeric"
                value={handlingCost}
                onChangeText={(val) => { setHandlingCost(val); setCostsEdited(true); }}
              />
            </View>
            <View style={styles.costItem}>
              <Text style={styles.costLabel}>{t.storageCost}</Text>
              <TextInput
                style={styles.smallInput}
                keyboardType="numeric"
                value={storageCost}
                onChangeText={(val) => { setStorageCost(val); setCostsEdited(true); }}
              />
            </View>
            <View style={styles.costItem}>
              <Text style={styles.costLabel}>{t.spoilageRisk}</Text>
              <TextInput
                style={styles.smallInput}
                keyboardType="numeric"
                value={spoilageRisk}
                onChangeText={(val) => { setSpoilageRisk(val); setSpoilageEdited(true); }}
              />
            </View>
          </View>
        )}

        {error ? (
          <View style={styles.errorBox}>
            <Ionicons name="alert-circle" size={16} color={COLORS.dangerRed} />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        <GradientButton
          title={loading ? t.calculating : t.calculateDecision}
          onPress={handleCalculate}
          loading={loading}
          style={{ marginTop: 14 }}
        />
      </Card>

      {/* Result Display */}
      {result && (
        <View style={styles.resultContainer}>
          {/* Recommendation Banner */}
          <LinearGradient
            colors={['rgba(0, 242, 254, 0.15)', 'rgba(79, 172, 254, 0.05)']}
            style={styles.recBanner}
          >
            <View style={styles.recTop}>
              <View style={styles.recBadgeRow}>
                <Ionicons name="sparkles" size={18} color={COLORS.cyan} />
                <Text style={styles.recBadgeText}>{t.recommended}</Text>
              </View>
              {result.uplift_vs_sell_now_pct > 0 && (
                <Badge
                  label={`+${result.uplift_vs_sell_now_pct}% ${lang === 'bn' ? 'বেশি লাভ' : 'uplift'}`}
                  variant="green"
                />
              )}
            </View>
            <Text style={styles.recActionText}>
              {result.options?.find((o) => o.id === result.recommended)?.label || result.recommended}
            </Text>
          </LinearGradient>

          {/* Options Comparison (Sell Now vs Wait) */}
          <Text style={styles.sectionHeading}>{t.incomeRange}</Text>

          {result.options?.map((opt) => {
            const isBest = opt.id === result.recommended;
            return (
              <Card key={opt.id} glow={isBest} style={isBest && styles.bestCard}>
                <View style={styles.optHeader}>
                  <Text style={[styles.optLabel, isBest && { color: COLORS.cyan }]}>
                    {opt.label}
                  </Text>
                  {isBest && <Badge label="★ Best" variant="cyan" />}
                </View>

                {/* Range stats */}
                <View style={styles.rangeRow}>
                  <View style={styles.rangeCol}>
                    <Text style={styles.rangeLabel}>{t.downside}</Text>
                    <Text style={styles.rangeVal}>৳{Math.round(opt.net?.downside || 0)}</Text>
                  </View>
                  <View style={styles.rangeDivider} />
                  <View style={styles.rangeCol}>
                    <Text style={styles.rangeLabel}>{t.base}</Text>
                    <Text style={[styles.rangeVal, { color: COLORS.neonGreen }]}>
                      ৳{Math.round(opt.net?.base || 0)}
                    </Text>
                  </View>
                  <View style={styles.rangeDivider} />
                  <View style={styles.rangeCol}>
                    <Text style={styles.rangeLabel}>{t.best}</Text>
                    <Text style={styles.rangeVal}>৳{Math.round(opt.net?.best || 0)}</Text>
                  </View>
                </View>

                {opt.forecast_price_range && (
                  <Text style={styles.forecastRange}>
                    📊 {lang === 'bn' ? 'সম্ভাব্য দাম:' : 'Forecast Price:'} ৳{opt.forecast_price_range[0]} - ৳{opt.forecast_price_range[2]} / kg
                  </Text>
                )}
              </Card>
            );
          })}

          {/* Explanation Box */}
          {result.explanation && (
            <Card>
              <Text style={styles.explainTitle}>💡 {t.explanation}</Text>
              {result.explanation.map((item, idx) => (
                <Text key={idx} style={styles.explainBullet}>
                  • {item}
                </Text>
              ))}
              <Text style={styles.disclaimer}>{result.disclaimer}</Text>
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
  inputLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  chipScroll: {
    flexDirection: 'row',
    marginBottom: 14,
  },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 10,
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    marginRight: 8,
  },
  chipActive: {
    borderColor: COLORS.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.15)',
  },
  chipText: {
    color: COLORS.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  chipTextActive: {
    color: COLORS.cyan,
    fontWeight: '700',
  },
  row: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 14,
  },
  halfCol: {
    flex: 1,
  },
  input: {
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: COLORS.textPrimary,
    fontSize: 14,
  },
  gradeRow: {
    flexDirection: 'row',
    gap: 6,
  },
  gradeBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    borderRadius: 8,
  },
  gradeBtnActive: {
    borderColor: COLORS.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.15)',
  },
  gradeText: {
    color: COLORS.textMuted,
    fontWeight: '700',
  },
  gradeTextActive: {
    color: COLORS.cyan,
  },
  accordionHeader: {
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
    marginTop: 6,
  },
  accordionTitle: {
    color: COLORS.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  advancedBox: {
    backgroundColor: 'rgba(0,0,0,0.25)',
    padding: 12,
    borderRadius: 10,
    marginBottom: 10,
  },
  costItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  costLabel: {
    color: COLORS.textMuted,
    fontSize: 12,
    flex: 1,
  },
  smallInput: {
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    color: COLORS.textPrimary,
    fontSize: 13,
    width: 70,
    textAlign: 'center',
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    padding: 10,
    backgroundColor: 'rgba(255, 82, 82, 0.1)',
    borderRadius: 8,
    marginTop: 8,
  },
  errorText: {
    color: COLORS.dangerRed,
    fontSize: 12,
  },
  resultContainer: {
    marginTop: 20,
  },
  recBanner: {
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.cyan,
    marginBottom: 18,
  },
  recTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 6,
  },
  recBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  recBadgeText: {
    color: COLORS.cyan,
    fontSize: 12.5,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  recActionText: {
    fontSize: 16,
    fontWeight: '800',
    color: COLORS.textPrimary,
    lineHeight: 22,
    marginTop: 4,
    flexShrink: 1,
  },
  sectionHeading: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 10,
  },
  bestCard: {
    borderColor: COLORS.cyan,
  },
  optHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  optLabel: {
    fontSize: 13.5,
    fontWeight: '700',
    color: COLORS.textPrimary,
    flex: 1,
    flexShrink: 1,
    marginRight: 8,
  },
  rangeRow: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: 'center',
  },
  rangeCol: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 2,
  },
  rangeLabel: {
    fontSize: 9.5,
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    textAlign: 'center',
  },
  rangeVal: {
    fontSize: 13.5,
    fontWeight: '800',
    color: COLORS.textPrimary,
    marginTop: 2,
    textAlign: 'center',
  },
  rangeDivider: {
    width: 1,
    height: 20,
    backgroundColor: COLORS.borderLight,
  },
  forecastRange: {
    fontSize: 11,
    color: COLORS.textSecondary,
    marginTop: 10,
  },
  explainTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.cyan,
    marginBottom: 6,
  },
  explainBullet: {
    fontSize: 12,
    color: COLORS.textSecondary,
    lineHeight: 18,
    marginBottom: 4,
  },
  disclaimer: {
    fontSize: 10,
    color: COLORS.textMuted,
    fontStyle: 'italic',
    marginTop: 8,
  },
});
