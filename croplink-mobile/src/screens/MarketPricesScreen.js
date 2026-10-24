import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import api from '../api/agrisphereApi';

const CROPS = ['tomato', 'potato', 'onion', 'brinjal', 'chili', 'cabbage', 'rice'];
const MARKETS = ['Dhaka', 'Chattogram', 'Rajshahi', 'Bogura', 'Khulna'];

export default function MarketPricesScreen() {
  const { t, lang } = useAuth();
  const [selectedCrop, setSelectedCrop] = useState('tomato');
  const [selectedMarket, setSelectedMarket] = useState('Dhaka');
  const [forecast, setForecast] = useState(null);
  const [todayPrices, setTodayPrices] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [todayRes, forecastRes] = await Promise.all([
        api.getTodayPrices(selectedMarket),
        api.getForecast(selectedCrop, selectedMarket),
      ]);
      if (todayRes && todayRes.prices) {
        setTodayPrices(todayRes.prices);
      }
      setForecast(forecastRes);
    } catch (_) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedCrop, selectedMarket]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.headerBox}>
        <Text style={styles.title}>{t.forecastTitle}</Text>
        <Text style={styles.subtitle}>
          {lang === 'bn' ? 'দৈনিক বাজার রেট ও AI দ্বারা মূল্যের আগাম হিসাব' : 'Daily wholesale rates & ML future price projection'}
        </Text>
      </View>

      {/* Market Selector */}
      <Text style={styles.selectorLabel}>{t.market}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.scrollRow}>
        {MARKETS.map((m) => (
          <TouchableOpacity
            key={m}
            onPress={() => setSelectedMarket(m)}
            style={[styles.marketChip, selectedMarket === m && styles.marketChipActive]}
          >
            <Text style={[styles.marketText, selectedMarket === m && styles.marketTextActive]}>
              {m}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Crop Selector */}
      <Text style={styles.selectorLabel}>{t.crop}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.scrollRow}>
        {CROPS.map((c) => (
          <TouchableOpacity
            key={c}
            onPress={() => setSelectedCrop(c)}
            style={[styles.cropChip, selectedCrop === c && styles.cropChipActive]}
          >
            <Text style={[styles.cropText, selectedCrop === c && styles.cropTextActive]}>
              {c.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {loading ? (
        <View style={styles.loaderBox}>
          <ActivityIndicator size="large" color={COLORS.cyan} />
          <Text style={styles.loaderText}>{t.loading}</Text>
        </View>
      ) : (
        <>
          {/* Visible Data Source / Synthetic Banner */}
          {forecast && (
            <View style={{
              backgroundColor: forecast.is_synthetic ? 'rgba(255, 171, 0, 0.15)' : 'rgba(0, 242, 254, 0.15)',
              borderWidth: 1,
              borderColor: forecast.is_synthetic ? COLORS.warningOrange : COLORS.cyan,
              borderRadius: 8,
              padding: 10,
              marginBottom: 12,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 8,
            }}>
              <Ionicons
                name={forecast.is_synthetic ? 'alert-circle-outline' : 'shield-checkmark-outline'}
                size={18}
                color={forecast.is_synthetic ? COLORS.warningOrange : COLORS.cyan}
              />
              <Text style={{
                color: forecast.is_synthetic ? COLORS.warningOrange : COLORS.cyan,
                fontSize: 12,
                flex: 1,
                fontWeight: '600',
              }}>
                {forecast.is_synthetic
                  ? (lang === 'bn' ? `সিন্থেটিক ডেটা (উৎস: ${forecast.data_source || 'synthetic'}) • বয়স: ${forecast.data_age_days ?? 0} দিন` : `Synthetic Data (Source: ${forecast.data_source || 'synthetic'}) • Age: ${forecast.data_age_days ?? 0}d`)
                  : (lang === 'bn' ? `বাস্তব বাজার ডেটা (উৎস: ${forecast.data_source})` : `Real Data (Source: ${forecast.data_source})`)}
              </Text>
            </View>
          )}

          {/* AI 7 & 14 Day Forecast Card */}
          {forecast && (
            <Card glow>
              <View style={styles.forecastHeader}>
                <View>
                  <Text style={styles.cardSectionTitle}>
                    {selectedCrop.toUpperCase()} — {selectedMarket}
                  </Text>
                  <Text style={styles.forecastCurrent}>
                    {t.currentPrice}: <Text style={{ color: COLORS.cyan, fontWeight: '800' }}>৳{forecast.current_price != null ? forecast.current_price.toFixed(1) : '—'}/kg</Text>
                  </Text>
                </View>
                <Badge
                  label={forecast.trend === 'up' ? '▲ Trend Up' : forecast.trend === 'down' ? '▼ Trend Down' : '● Stable'}
                  variant={forecast.trend === 'up' ? 'green' : forecast.trend === 'down' ? 'red' : 'cyan'}
                />
              </View>

              {/* 7-day and 14-day comparison boxes */}
              <View style={styles.forecastBoxesRow}>
                {/* 7 Days */}
                <View style={styles.forecastBox}>
                  <Text style={styles.forecastBoxTitle}>📅 {t.forecast7d}</Text>
                  <Text style={styles.forecastPrice}>৳{forecast.h7?.base != null ? forecast.h7.base.toFixed(1) : '—'}</Text>
                  <Text style={styles.forecastRangeText}>
                    ({forecast.h7?.low != null ? forecast.h7.low.toFixed(1) : '—'} - {forecast.h7?.high != null ? forecast.h7.high.toFixed(1) : '—'})
                  </Text>
                </View>

                {/* 14 Days */}
                <View style={styles.forecastBox}>
                  <Text style={styles.forecastBoxTitle}>📅 {t.forecast14d}</Text>
                  <Text style={styles.forecastPrice}>৳{forecast.h14?.base != null ? forecast.h14.base.toFixed(1) : '—'}</Text>
                  <Text style={styles.forecastRangeText}>
                    ({forecast.h14?.low != null ? forecast.h14.low.toFixed(1) : '—'} - {forecast.h14?.high != null ? forecast.h14.high.toFixed(1) : '—'})
                  </Text>
                </View>
              </View>

              {/* Visual confidence bars */}
              <View style={styles.barSection}>
                <Text style={styles.barLabel}>{lang === 'bn' ? 'পূর্বাভাস অনিশ্চয়তা পরিসীমা' : 'Forecast Range Spread'}</Text>
                <View style={styles.barBackground}>
                  <View style={[styles.barFill, { width: '75%' }]} />
                </View>
              </View>
            </Card>
          )}

          {/* Today's Market Rates for All Crops */}
          <Text style={[styles.selectorLabel, { marginTop: 12 }]}>{t.todayPrices}</Text>
          <Card>
            {todayPrices.map((item, i) => {
              const priceVal = (item.price_bdt_kg ?? item.price) != null ? Number(item.price_bdt_kg ?? item.price).toFixed(1) : '—';
              const changeVal = Number(item.change_1d_pct ?? item.change_pct ?? 0);
              const marketText = item.market || selectedMarket || 'Dhaka';

              return (
                <View
                  key={i}
                  style={[
                    styles.priceItem,
                    i < todayPrices.length - 1 && styles.priceItemBorder,
                  ]}
                >
                  <View style={styles.cropInfoCol}>
                    <Text style={styles.cropTitleText}>{(item.crop || 'crop').toUpperCase()}</Text>
                    <Text style={styles.cropSubText}>{marketText}</Text>
                  </View>
                  <View style={styles.rateCol}>
                    <Text style={styles.rateVal}>৳{priceVal} / kg</Text>
                    <Text
                      style={[
                        styles.changeVal,
                        { color: changeVal >= 0 ? COLORS.neonGreen : COLORS.dangerRed },
                      ]}
                    >
                      {changeVal >= 0 ? `▲ +${changeVal}%` : `▼ ${changeVal}%`}
                    </Text>
                  </View>
                </View>
              );
            })}
          </Card>
        </>
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
  selectorLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  scrollRow: {
    flexDirection: 'row',
    marginBottom: 14,
  },
  marketChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 10,
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    marginRight: 8,
  },
  marketChipActive: {
    borderColor: COLORS.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.15)',
  },
  marketText: {
    color: COLORS.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  marketTextActive: {
    color: COLORS.cyan,
    fontWeight: '700',
  },
  cropChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: COLORS.bgInput,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    marginRight: 8,
  },
  cropChipActive: {
    borderColor: COLORS.neonGreen,
    backgroundColor: 'rgba(0, 230, 118, 0.15)',
  },
  cropText: {
    color: COLORS.textMuted,
    fontSize: 11,
    fontWeight: '600',
  },
  cropTextActive: {
    color: COLORS.neonGreen,
    fontWeight: '700',
  },
  loaderBox: {
    paddingVertical: 40,
    alignItems: 'center',
    gap: 10,
  },
  loaderText: {
    color: COLORS.textMuted,
    fontSize: 13,
  },
  forecastHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  cardSectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  forecastCurrent: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 3,
  },
  forecastBoxesRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  forecastBox: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  forecastBoxTitle: {
    fontSize: 11,
    color: COLORS.textMuted,
    fontWeight: '600',
    textAlign: 'center',
  },
  forecastPrice: {
    fontSize: 17,
    fontWeight: '800',
    color: COLORS.cyan,
    marginVertical: 4,
    textAlign: 'center',
  },
  forecastRangeText: {
    fontSize: 10,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
  barSection: {
    marginTop: 6,
  },
  barLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
    marginBottom: 6,
  },
  barBackground: {
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 3,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    backgroundColor: COLORS.cyan,
  },
  priceItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
  },
  priceItemBorder: {
    borderBottomWidth: 1,
    borderBottomColor: COLORS.borderLight,
  },
  cropInfoCol: {},
  cropTitleText: {
    fontSize: 14,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  cropSubText: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  rateCol: {
    alignItems: 'flex-end',
  },
  rateVal: {
    fontSize: 14,
    fontWeight: '700',
    color: COLORS.cyan,
  },
  changeVal: {
    fontSize: 11,
    fontWeight: '600',
  },
});
