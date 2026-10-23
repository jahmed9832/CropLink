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
    } catch (_) {
      // Mock plan aligned with backend pooling logic
      setPoolPlan({
        demand_id: demand.id,
        target_quantity_kg: demand.min_quantity_kg,
        matched_lots_count: 3,
        total_pooled_kg: demand.min_quantity_kg,
        logistics_cost_savings_pct: 22.5,
        estimated_price_bdt: demand.target_price_bdt,
        farmer_allocations: [
          { farmer_name: user?.name || 'আপনার অংশ (You)', allocated_kg: 400, expected_payout_bdt: 400 * demand.target_price_bdt * 0.96 },
          { farmer_name: 'আব্দুল করিম (Gazipur)', allocated_kg: 500, expected_payout_bdt: 500 * demand.target_price_bdt * 0.96 },
          { farmer_name: 'মো: রফিকুল (Tangail)', allocated_kg: 300, expected_payout_bdt: 300 * demand.target_price_bdt * 0.96 },
        ],
      });
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
                  {d.crop?.toUpperCase()} • Grade {d.grade} • 📍 {d.destination || 'Dhaka'}
                </Text>
              </View>
              <Badge label={`৳${d.target_price_bdt}/kg`} variant="green" />
            </View>

            <View style={styles.qtyRow}>
              <Text style={styles.qtyLabel}>
                {lang === 'bn' ? 'ন্যূনতম চাহিদা:' : 'Min Required:'}
              </Text>
              <Text style={styles.qtyVal}>{d.min_quantity_kg} kg</Text>
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
                <Text style={styles.bannerVal}>{poolPlan.total_pooled_kg} kg</Text>
              </View>
              <View style={styles.divider} />
              <View style={styles.bannerCol}>
                <Text style={styles.bannerLabel}>
                  {lang === 'bn' ? 'পরিবহন সাশ্রয়' : 'Logistics Saving'}
                </Text>
                <Text style={[styles.bannerVal, { color: COLORS.neonGreen }]}>
                  {poolPlan.logistics_cost_savings_pct || 22}%
                </Text>
              </View>
            </View>

            <Text style={styles.allocHeader}>
              {lang === 'bn' ? 'অংশগ্রহণকারী কৃষকদের পাওনা:' : 'Farmer Allocation & Payout:'}
            </Text>

            {poolPlan.farmer_allocations?.map((f, idx) => (
              <View key={idx} style={styles.allocRow}>
                <View>
                  <Text style={styles.farmerName}>{f.farmer_name}</Text>
                  <Text style={styles.allocKg}>{f.allocated_kg} kg বরাদ্দ</Text>
                </View>
                <Text style={styles.allocMoney}>
                  ৳{Math.round(f.expected_payout_bdt).toLocaleString()}
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
