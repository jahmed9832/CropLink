import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import api from '../api/agrisphereApi';

export default function DashboardScreen({ onNavigate }) {
  const { user, t, lang } = useAuth();
  const [todayPrices, setTodayPrices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Today's Market Prices
      const pricesRes = await api.getTodayPrices();
      if (pricesRes) {
        const raw = Array.isArray(pricesRes) ? pricesRes : (pricesRes.prices || []);
        setTodayPrices(raw.slice(0, 5));
      }

      // 2. Fetch Farmer Dashboard if farmer
      if (user && user.user_id && user.role === 'farmer') {
        const dashRes = await api.getFarmerDashboard(user.user_id);
        setSummary(dashRes);
      }
    } catch (_) {
      // Graceful fallback for offline/loading
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [user]);

  const quickActions = [
    {
      id: 'decision',
      title: t.netProfitAI,
      subtitle: lang === 'bn' ? 'বেচবেন না অপেক্ষা করবেন?' : 'Sell now vs Wait analysis',
      icon: 'calculator-outline',
      colors: ['#10B981', '#0EA5E9'],
      badge: lang === 'bn' ? 'প্রধান ইঞ্জিন' : 'Core AI',
    },
    {
      id: 'grading',
      title: t.photoGrade,
      subtitle: lang === 'bn' ? 'ছবি তুলে মান ও QR পাসপোর্ট' : 'Camera grading & QR passport',
      icon: 'camera-outline',
      colors: ['#059669', '#10B981'],
      badge: lang === 'bn' ? 'গ্রেড A/B/C' : 'Vision AI',
    },
    {
      id: 'market',
      title: t.marketForecast,
      subtitle: lang === 'bn' ? '৭ ও ১৪ দিনের দামের পূর্বাভাস' : '7/14-Day Price Forecast',
      icon: 'trending-up-outline',
      colors: ['#2563EB', '#38BDF8'],
      badge: lang === 'bn' ? 'পূর্বাভাস' : 'Forecast',
    },
    {
      id: 'pooling',
      title: t.supplyPool,
      subtitle: lang === 'bn' ? 'একাধিক কৃষকের যৌথ সাপ্লাই' : 'Bulk orders fulfillment',
      icon: 'people-outline',
      colors: ['#0284C7', '#0EA5E9'],
      badge: lang === 'bn' ? 'সমবায়' : 'Cooperative',
    },
    {
      id: 'assistant',
      title: t.aiAssistant,
      subtitle: lang === 'bn' ? 'বাংলা ও Banglish এ প্রশ্ন করুন' : 'Bengali & Banglish Voice/AI',
      icon: 'chatbubble-ellipses-outline',
      colors: ['#8B5CF6', '#EC4899'],
      badge: lang === 'bn' ? 'অ্যাসিস্ট্যান্ট' : 'Gemini AI',
    },
    {
      id: 'orders',
      title: t.myOrders,
      subtitle: lang === 'bn' ? 'ডেলিভারি ও কোয়ালিটি প্রমাণ' : 'Tracking & Dispute Evidence',
      icon: 'receipt-outline',
      colors: ['#D97706', '#F59E0B'],
      badge: lang === 'bn' ? 'ট্র্যাকিং' : 'Orders',
    },
  ];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={fetchDashboardData} tintColor={COLORS.cyan} />
      }
    >
      {/* Welcome Banner */}
      <LinearGradient colors={COLORS.gradientHero} style={styles.heroCard}>
        <View style={styles.heroTop}>
          <View>
            <Text style={styles.welcomeText}>
              {t.welcome}, {user?.name || (user?.role === 'farmer' ? t.farmer : t.buyer)}
            </Text>
            <Text style={styles.districtText}>
              📍 {user?.district || 'Gazipur'}, Bangladesh
            </Text>
          </View>
          <Badge
            label={user?.role === 'buyer' ? t.buyer : t.farmer}
            variant={user?.role === 'buyer' ? 'purple' : 'green'}
          />
        </View>

        {/* Mini stats row */}
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{summary?.active_lots_count ?? 3}</Text>
            <Text style={styles.statLabel}>{t.activeLots}</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{summary?.open_offers_count ?? 5}</Text>
            <Text style={styles.statLabel}>{t.openOffers}</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Text style={[styles.statNum, { color: COLORS.neonGreen }]}>
              {summary?.buyer_reliability_score ? `${summary.buyer_reliability_score}%` : '94%'}
            </Text>
            <Text style={styles.statLabel}>
              {lang === 'bn' ? 'বিশ্বস্ততা' : 'Trust Score'}
            </Text>
          </View>
        </View>
      </LinearGradient>

      {/* Section: Quick Actions */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{t.quickActions}</Text>
        <Text style={styles.sectionSub}>
          {lang === 'bn' ? 'কৃষকের সব সমাধান এক স্ক্রিনে' : 'All tools at your fingertips'}
        </Text>
      </View>

      <View style={styles.grid}>
        {quickActions.map((action) => (
          <TouchableOpacity
            key={action.id}
            activeOpacity={0.8}
            onPress={() => onNavigate(action.id)}
            style={styles.gridItem}
          >
            <LinearGradient
              colors={['rgba(255, 255, 255, 0.05)', 'rgba(255, 255, 255, 0.01)']}
              style={styles.actionCard}
            >
              <View style={styles.actionTop}>
                <LinearGradient colors={action.colors} style={styles.iconCircle}>
                  <Ionicons name={action.icon} size={20} color="#070B14" />
                </LinearGradient>
                <Badge label={action.badge} variant="cyan" style={styles.miniBadge} />
              </View>
              <Text style={styles.actionTitle} numberOfLines={1} ellipsizeMode="tail">{action.title}</Text>
              <Text style={styles.actionSub} numberOfLines={2} ellipsizeMode="tail">
                {action.subtitle}
              </Text>
            </LinearGradient>
          </TouchableOpacity>
        ))}
      </View>

      {/* Section: Today's Market Price Ticker */}
      <View style={styles.sectionHeader}>
        <View style={styles.titleRow}>
          <Text style={styles.sectionTitle}>{t.todayPrices}</Text>
          <TouchableOpacity onPress={() => onNavigate('market')}>
            <Text style={styles.viewAllText}>{t.viewAll} →</Text>
          </TouchableOpacity>
        </View>
      </View>

      <Card glow>
        {todayPrices.length === 0 ? (
          <View style={styles.placeholderRow}>
            <Ionicons name="stats-chart-outline" size={20} color={COLORS.cyan} />
            <Text style={styles.placeholderText}>
              {lang === 'bn' ? 'বাজার দর লোড হচ্ছে...' : 'Loading market prices...'}
            </Text>
          </View>
        ) : (
          todayPrices.map((p, idx) => {
            const priceVal = Number(p.price_bdt_kg ?? p.price ?? 85).toFixed(1);
            const changeVal = Number(p.change_1d_pct ?? p.change_pct ?? 0);
            const marketText = p.market || 'Dhaka';

            return (
              <View
                key={idx}
                style={[
                  styles.priceRow,
                  idx < todayPrices.length - 1 && styles.priceRowBorder,
                ]}
              >
                <View>
                  <Text style={styles.cropName}>{(p.crop || 'crop').toUpperCase()}</Text>
                  <Text style={styles.marketName}>{marketText}</Text>
                </View>
                <View style={styles.priceCol}>
                  <Text style={styles.priceNum}>৳{priceVal} / kg</Text>
                  <Text
                    style={[
                      styles.priceChange,
                      {
                        color:
                          changeVal >= 0 ? COLORS.neonGreen : COLORS.dangerRed,
                      },
                    ]}
                  >
                    {changeVal >= 0 ? `▲ +${changeVal}%` : `▼ ${changeVal}%`}
                  </Text>
                </View>
              </View>
            );
          })
        )}
      </Card>
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
  heroCard: {
    borderRadius: 20,
    padding: 18,
    borderWidth: 1,
    borderColor: COLORS.borderAccent,
    marginBottom: 22,
  },
  heroTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  welcomeText: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  districtText: {
    fontSize: 12,
    color: COLORS.cyan,
    marginTop: 3,
  },
  statsRow: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 14,
    paddingVertical: 12,
    alignItems: 'center',
  },
  statBox: {
    flex: 1,
    alignItems: 'center',
  },
  statNum: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  statLabel: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 24,
    backgroundColor: COLORS.borderLight,
  },
  sectionHeader: {
    marginBottom: 12,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  sectionSub: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  viewAllText: {
    fontSize: 12,
    color: COLORS.cyan,
    fontWeight: '600',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  gridItem: {
    width: '48%',
    marginBottom: 12,
  },
  actionCard: {
    backgroundColor: COLORS.bgCard,
    borderRadius: 16,
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    minHeight: 148,
    justifyContent: 'space-between',
  },
  actionTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  miniBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  actionTitle: {
    fontSize: 13.5,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginTop: 6,
  },
  actionSub: {
    fontSize: 11,
    color: COLORS.textMuted,
    lineHeight: 15,
    marginTop: 2,
  },
  placeholderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
  },
  placeholderText: {
    color: COLORS.textMuted,
    fontSize: 13,
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
  },
  priceRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: COLORS.borderLight,
  },
  cropName: {
    fontSize: 14,
    fontWeight: '700',
    color: COLORS.textPrimary,
  },
  marketName: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  priceCol: {
    alignItems: 'flex-end',
  },
  priceNum: {
    fontSize: 14,
    fontWeight: '700',
    color: COLORS.cyan,
  },
  priceChange: {
    fontSize: 11,
    fontWeight: '600',
  },
});
