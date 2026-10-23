import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import GradientButton from '../components/GradientButton';
import api from '../api/agrisphereApi';

export default function OrdersScreen() {
  const { t, lang } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    async function loadOrders() {
      setLoading(true);
      try {
        const res = await api.getOrders();
        if (res && Array.isArray(res) && res.length > 0) {
          setOrders(res);
        } else {
          // Fallback demo orders for prototype demonstration
          setOrders([
            {
              id: 'ord_901',
              crop: 'tomato',
              quantity_kg: 500,
              agreed_price_bdt: 88,
              agreed_grade: 'A',
              status: 'delivered',
              buyer_name: 'Shwapno Super Shop',
              created_at: '2026-10-22',
            },
            {
              id: 'ord_902',
              crop: 'potato',
              quantity_kg: 1000,
              agreed_price_bdt: 36,
              agreed_grade: 'A',
              status: 'in_delivery',
              buyer_name: 'Meena Retail Ltd',
              created_at: '2026-10-21',
            },
            {
              id: 'ord_903',
              crop: 'onion',
              quantity_kg: 800,
              agreed_price_bdt: 70,
              agreed_grade: 'B',
              status: 'disputed',
              buyer_name: 'Karwan Bazar Aggregator',
              created_at: '2026-10-20',
            },
          ]);
        }
      } catch (_) {
        // demo fallback
      } finally {
        setLoading(false);
      }
    }

    loadOrders();
  }, []);

  const handleViewEvidence = async (orderId) => {
    setEvidenceLoading(true);
    setModalVisible(true);
    try {
      const ev = await api.getDisputeEvidence(orderId);
      setSelectedEvidence(ev);
    } catch (_) {
      // Mock evidence aligned with backend dispute model
      setSelectedEvidence({
        order_id: orderId,
        crop: 'onion',
        pre_sale_evidence: {
          grade: 'B',
          suggested_price: 70,
          timestamp: '2026-10-20 10:30 AM',
          photo_verified: true,
        },
        delivery_observation: {
          buyer_reported_grade: 'C',
          buyer_reported_weight_kg: 760,
          proposed_deduction_pct: 12.0,
          reason: 'Moisture damage observed in 4 sacks during transit',
          timestamp: '2026-10-20 04:15 PM',
        },
        ai_recommendation:
          lang === 'bn'
            ? 'উভয় পক্ষের রেকর্ড অনুযায়ী ৪% সামঞ্জস্যপূর্ণ রিবেট প্রদানের সুপারিশ করা হচ্ছে। কোনো পক্ষকেই এককভাবে দায়ী করা হয়নি।'
            : 'Evidence suggests minor transit moisture. Recommended fair compromise: 4% rebate instead of 12%. Neither party declared at full fault.',
      });
    } finally {
      setEvidenceLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'paid':
        return <Badge label={t.paid} variant="green" />;
      case 'delivered':
        return <Badge label={t.delivered} variant="cyan" />;
      case 'in_delivery':
        return <Badge label={t.inDelivery} variant="purple" />;
      case 'disputed':
        return <Badge label={t.dispute} variant="orange" />;
      default:
        return <Badge label={t.matched} variant="cyan" />;
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.headerBox}>
        <Text style={styles.title}>{t.ordersTitle}</Text>
        <Text style={styles.subtitle}>
          {lang === 'bn' ? 'চালানের স্থিতি ও বিরোধ নিষ্পত্তি এভিডেন্স' : 'Order tracking & side-by-side dispute evidence'}
        </Text>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={COLORS.cyan} style={{ marginVertical: 30 }} />
      ) : (
        orders.map((order) => {
          const qty = order.total_kg ?? order.quantity_kg ?? order.quantity ?? (order.allocations ? order.allocations.reduce((sum, a) => sum + (a.allocated_kg || 0), 0) : 500);
          const price = order.agreed_price ?? order.agreed_price_bdt ?? order.price ?? 85;
          const grade = order.agreed_grade ?? order.grade ?? 'A';
          const formattedDate = order.created_at ? order.created_at.split('T')[0] : '2026-10-22';

          return (
            <Card key={order.id} glow={order.status === 'disputed'}>
              <View style={styles.orderTop}>
                <View style={{ flex: 1, marginRight: 8 }}>
                  <Text style={styles.orderIdText} numberOfLines={1}>{t.orderId} {order.id}</Text>
                  <Text style={styles.buyerNameText} numberOfLines={1}>{order.buyer_name || 'Shwapno / Wholesale'}</Text>
                </View>
                {getStatusBadge(order.status)}
              </View>

              <View style={styles.orderSpecsRow}>
                <View style={styles.specBox}>
                  <Text style={styles.specLabel}>{t.crop}</Text>
                  <Text style={styles.specVal}>{(order.crop || 'tomato').toUpperCase()}</Text>
                </View>
                <View style={styles.specBox}>
                  <Text style={styles.specLabel}>{t.quantity}</Text>
                  <Text style={styles.specVal}>{qty} kg</Text>
                </View>
                <View style={styles.specBox}>
                  <Text style={styles.specLabel}>{lang === 'bn' ? 'দর' : 'Rate'}</Text>
                  <Text style={[styles.specVal, { color: COLORS.cyan }]}>
                    ৳{price}/kg
                  </Text>
                </View>
                <View style={styles.specBox}>
                  <Text style={styles.specLabel}>{t.grade}</Text>
                  <Text style={styles.specVal}>{grade}</Text>
                </View>
              </View>

              <View style={styles.orderBottom}>
                <Text style={styles.dateText}>📅 {formattedDate}</Text>
                <TouchableOpacity
                  onPress={() => handleViewEvidence(order.id)}
                  style={styles.evidenceBtn}
                >
                  <Ionicons name="document-text-outline" size={15} color={COLORS.cyan} />
                  <Text style={styles.evidenceBtnText} numberOfLines={1}>
                    {lang === 'bn' ? 'এভিডেন্স রিপোর্ট' : 'Evidence Report'}
                  </Text>
                </TouchableOpacity>
              </View>
            </Card>
          );
        })
      )}

      {/* Side-by-Side Dispute Evidence Modal */}
      <Modal visible={modalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>⚖️ {t.viewEvidence}</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.closeBtn}>
                <Ionicons name="close" size={20} color={COLORS.textPrimary} />
              </TouchableOpacity>
            </View>

            {evidenceLoading || !selectedEvidence ? (
              <ActivityIndicator size="large" color={COLORS.cyan} style={{ padding: 40 }} />
            ) : (
              <ScrollView>
                <Text style={styles.evSub}>
                  {lang === 'bn'
                    ? 'কৃষকের পূর্ব-বিক্রয় রেকর্ড বনাম বায়ারের ডেলিভারি পর্যবেক্ষণ'
                    : 'Pre-sale verified batch vs Delivery observation'}
                </Text>

                {/* Side-by-Side comparison cards */}
                <View style={styles.compareRow}>
                  {/* Farmer Record */}
                  <View style={styles.compareCol}>
                    <Text style={styles.colTitle}>👨‍🌾 {lang === 'bn' ? 'কৃষকের রেকর্ড' : 'Farmer Record'}</Text>
                    <Text style={styles.evField}>
                      {t.grade}: <Text style={{ color: COLORS.neonGreen, fontWeight: '700' }}>{selectedEvidence.pre_sale_evidence?.grade}</Text>
                    </Text>
                    <Text style={styles.evField}>
                      {lang === 'bn' ? 'প্রস্তাবিত দর:' : 'Rate:'} ৳{selectedEvidence.pre_sale_evidence?.suggested_price}
                    </Text>
                    <Badge label="Photo Verified" variant="green" style={{ marginTop: 8 }} />
                  </View>

                  {/* Buyer Report */}
                  <View style={styles.compareCol}>
                    <Text style={styles.colTitle}>🏢 {lang === 'bn' ? 'বায়ারের দাবি' : 'Buyer Claim'}</Text>
                    <Text style={styles.evField}>
                      {t.grade}: <Text style={{ color: COLORS.warningOrange, fontWeight: '700' }}>{selectedEvidence.delivery_observation?.buyer_reported_grade}</Text>
                    </Text>
                    <Text style={styles.evField}>
                      {lang === 'bn' ? 'দাবীকৃত ছাড়:' : 'Deduction:'} {selectedEvidence.delivery_observation?.proposed_deduction_pct}%
                    </Text>
                    <Text style={[styles.evField, { fontSize: 11, color: COLORS.textMuted, marginTop: 4 }]}>
                      {selectedEvidence.delivery_observation?.reason}
                    </Text>
                  </View>
                </View>

                {/* AI Arbitrator Recommendation */}
                <Card glow style={{ marginTop: 14 }}>
                  <Text style={styles.aiRecTitle}>🤖 {lang === 'bn' ? 'নিরপেক্ষ AI পরামর্শ:' : 'Neutral AI Recommendation:'}</Text>
                  <Text style={styles.aiRecText}>
                    {selectedEvidence.ai_recommendation}
                  </Text>
                </Card>
              </ScrollView>
            )}
          </View>
        </View>
      </Modal>
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
  orderTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  orderIdText: {
    fontSize: 14,
    fontWeight: '800',
    color: COLORS.cyan,
  },
  buyerNameText: {
    fontSize: 13,
    color: COLORS.textPrimary,
    fontWeight: '600',
    marginTop: 2,
  },
  orderSpecsRow: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 10,
    paddingVertical: 10,
    marginBottom: 12,
  },
  specBox: {
    flex: 1,
    alignItems: 'center',
  },
  specLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
    textTransform: 'uppercase',
  },
  specVal: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginTop: 2,
  },
  orderBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
    paddingTop: 10,
  },
  dateText: {
    fontSize: 11,
    color: COLORS.textMuted,
  },
  evidenceBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  evidenceBtnText: {
    fontSize: 12,
    color: COLORS.cyan,
    fontWeight: '700',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.85)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: COLORS.bgCardSolid,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '85%',
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  closeBtn: {
    padding: 4,
  },
  evSub: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginBottom: 14,
  },
  compareRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  compareCol: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  colTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: COLORS.textPrimary,
    marginBottom: 8,
  },
  evField: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginBottom: 4,
  },
  aiRecTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: COLORS.cyan,
    marginBottom: 6,
  },
  aiRecText: {
    fontSize: 12,
    color: COLORS.textPrimary,
    lineHeight: 18,
  },
});
