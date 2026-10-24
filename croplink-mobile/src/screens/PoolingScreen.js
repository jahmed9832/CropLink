import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import GradientButton from '../components/GradientButton';
import api from '../api/agrisphereApi';

export default function PoolingScreen() {
  const { t, lang, user } = useAuth();
  const [demands, setDemands] = useState([]);
  const [selectedDemand, setSelectedDemand] = useState(null);
  const [poolPlan, setPoolPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [planning, setPlanning] = useState(false);

  useEffect(() => {
    async function loadDemands() {
      setLoading(true);
      try {
        const res = await api.getDemands();
        if (res && Array.isArray(res)) {
          setDemands(res);
        } else if (res && res.demands) {
          setDemands(res.demands);
        } else {
          // Fallback realistic demo demands if none exists yet
          setDemands([
            {
              id: 'dem_agri_101',
              buyer_name: 'Shwapno Super Shop (Procurement)',
              crop: 'tomato',
              min_quantity_kg: 1200,
              target_price_bdt: 88,
              grade: 'A',
              delivery_window_days: 3,
              destination: 'Dhaka Central Hub',
            },
            {
              id: 'dem_agri_102',
              buyer_name: 'Meena Bazar Institutional Buyer',
              crop: 'potato',
              min_quantity_kg: 2500,
              target_price_bdt: 36,
              grade: 'A',
              delivery_window_days: 5,
              destination: 'Bogura Hub',
            },
          ]);
        }
      } catch (_) {
        // Fallback for demo
        setDemands([
          {
            id: 'dem_agri_101',
            buyer_name: 'Shwapno Super Shop (Procurement)',
            crop: 'tomato',
            min_quantity_kg: 1200,
            target_price_bdt: 88,
            grade: 'A',
            delivery_window_days: 3,
            destination: 'Dhaka Central Hub',
          },
        ]);
      } finally {
        setLoading(false);
      }
    }

    loadDemands();
  }, []);

  const handleGeneratePool = async (demand) => {
    setSelectedDemand(demand);
    setPlanning(true);
    setPoolPlan(null);
    try {
      const res = await api.createPoolPlan(demand.id);
      setPoolPlan(res);
    } catch (err) {
      Alert.alert(
        lang === 'bn' ? 'পুল পরিকল্পনা ত্রুটি' : 'Pool Plan Error',
        err.message || (lang === 'bn' ? 'পুল পরিকল্পনা তৈরি করা যায়নি।' : 'Failed to generate pool plan.')
      );
    } finally {
      setPlanning(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.headerBox}>
        <Text style={styles.title}>{t.poolTitle}</Text>
        <Text style={styles.subtitle}>{t.poolSubtitle}</Text>
      </View>

      <Text style={styles.sectionTitle}>
        {lang === 'bn' ? 'খোলা পাইকারি চাহিদা (Bulk Demands)' : 'Open Bulk Demands'}
      </Text>

      {loading ? (
        <ActivityIndicator size="large" color={COLORS.cyan} style={{ marginVertical: 30 }} />
      ) : (
        demands.map((d) => (
          <Card key={d.id} glow={selectedDemand?.id === d.id}>
            <View style={styles.demandHeader}>
              <View>
                <Text style={styles.buyerName}>{d.buyer_name || 'Verified Buyer'}</Text>
                <Text style={styles.cropTag}>
                  {d.crop?.toUpperCase()} • Grade {d.min_grade || d.grade || 'C'} • 📍 {typeof d.location === 'object' ? (d.location?.district || d.location?.address || 'Dhaka') : (d.location || d.destination || 'Dhaka')}
                </Text>
              </View>
              <Badge label={`৳${d.price_per_kg ?? d.target_price_bdt}/kg`} variant="green" />
            </View>

            <View style={styles.qtyRow}>
              <Text style={styles.qtyLabel}>
                {lang === 'bn' ? 'ন্যূনতম চাহিদা:' : 'Min Required:'}
              </Text>
              <Text style={styles.qtyVal}>{d.min_quantity_kg || d.quantity_kg} kg</Text>
            </View>

            <GradientButton
              title={planning && selectedDemand?.id === d.id ? t.loading : t.combineSupply}
              onPress={() => handleGeneratePool(d)}
              loading={planning && selectedDemand?.id === d.id}
              style={{ marginTop: 12 }}
            />
          </Card>
        ))
      )}

      {/* Generated Pool Plan Breakdown */}
      {poolPlan && (
        <View style={styles.planContainer}>
          <Text style={[styles.sectionTitle, { color: COLORS.cyan }]}>
            🤝 {lang === 'bn' ? 'যৌথ পুলিং বাস্তবায়ন পরিকল্পনা' : 'Cooperative Fulfillment Plan'}
          </Text>

          <Card glow>
            <View style={styles.statBanner}>
              <View style={styles.bannerCol}>
                <Text style={styles.bannerLabel}>
                  {lang === 'bn' ? 'মোট যৌথ ফসল' : 'Total Volume'}
                </Text>
                <Text style={styles.bannerVal}>{poolPlan.pooled_kg} kg</Text>
              </View>
              <View style={styles.divider} />
              <View style={styles.bannerCol}>
                <Text style={styles.bannerLabel}>
                  {lang === 'bn' ? 'পূরণ হার' : 'Fill Rate'}
                </Text>
                <Text style={[styles.bannerVal, { color: COLORS.neonGreen }]}>
                  {poolPlan.fill_rate_pct}%
                </Text>
              </View>
            </View>

            <View style={[styles.qtyRow, { marginTop: 10 }]}>
              <Text style={styles.qtyLabel}>
                {lang === 'bn' ? 'প্রয়োজনীয় পরিমাণ:' : 'Required Volume:'}
              </Text>
              <Text style={styles.qtyVal}>{poolPlan.required_kg} kg</Text>
            </View>

            <Text style={styles.allocHeader}>
              {lang === 'bn' ? 'অংশগ্রহণকারী কৃষকদের বরাদ্দ ও পাওনা:' : 'Farmer Allocation & Payout:'}
            </Text>

            {poolPlan.allocations?.map((a, idx) => (
              <View key={idx} style={styles.allocRow}>
                <View>
                  <Text style={styles.farmerName}>
                    {a.farmer_id === user?.user_id ? (lang === 'bn' ? 'আপনার অংশ (You)' : 'Your Share') : a.farmer_id}
                  </Text>
                  <Text style={styles.allocKg}>{a.allocated_kg} kg বরাদ্দ</Text>
                  {a.logistics_share > 0 && (
                    <Text style={{ fontSize: 11, color: COLORS.textMuted }}>
                      {lang === 'bn' ? 'পরিবহন খরচ অংশ:' : 'Logistics share:'} ৳{a.logistics_share}
                    </Text>
                  )}
                </View>
                <Text style={styles.allocMoney}>
                  ৳{Math.round(a.expected_payment || 0).toLocaleString()}
                </Text>
              </View>
            ))}
          </Card>
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
  sectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 12,
  },
  demandHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  buyerName: {
    fontSize: 15,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  cropTag: {
    fontSize: 12,
    color: COLORS.cyan,
    marginTop: 3,
  },
  qtyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 6,
  },
  qtyLabel: {
    fontSize: 12,
    color: COLORS.textMuted,
  },
  qtyVal: {
    fontSize: 14,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  planContainer: {
    marginTop: 18,
  },
  statBanner: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 12,
    paddingVertical: 12,
    marginBottom: 14,
  },
  bannerCol: {
    flex: 1,
    alignItems: 'center',
  },
  bannerLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  bannerVal: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.cyan,
    marginTop: 3,
  },
  divider: {
    width: 1,
    height: 24,
    backgroundColor: COLORS.borderLight,
  },
  allocHeader: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textSecondary,
    marginBottom: 8,
  },
  allocRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.borderLight,
  },
  farmerName: {
    fontSize: 14,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  allocKg: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  allocMoney: {
    fontSize: 15,
    fontWeight: '800',
    color: COLORS.neonGreen,
  },
});
