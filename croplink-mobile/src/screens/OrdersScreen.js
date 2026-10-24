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

  const [evidenceError, setEvidenceError] = useState('');

  useEffect(() => {
    async function loadOrders() {
      setLoading(true);
      try {
        const res = await api.getOrders();
        if (res && Array.isArray(res)) {
          setOrders(res);
        } else {
          setOrders([]);
        }
      } catch (_) {
        setOrders([]);
      } finally {
        setLoading(false);
      }
    }

    loadOrders();
  }, []);

  const handleViewEvidence = async (orderId) => {
    setEvidenceLoading(true);
    setModalVisible(true);
    setSelectedEvidence(null);
    setEvidenceError('');
    try {
      const ev = await api.getDisputeEvidence(orderId);
      setSelectedEvidence(ev);
    } catch (err) {
      if (err.status === 404) {
        setEvidenceError(lang === 'bn' ? 'এখনো কোনো ডেলিভারি রেকর্ড করা হয়নি (no delivery recorded yet)' : 'no delivery recorded yet');
      } else {
        setEvidenceError(err.message || (lang === 'bn' ? 'এভিডেন্স লোড করা যায়নি' : 'Failed to load evidence report'));
      }
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
          const qty = order.total_kg ?? (order.allocations ? order.allocations.reduce((sum, a) => sum + (a.allocated_kg || 0), 0) : 0);
          const price = order.agreed_price ?? 0;
          const grade = order.grade ?? (order.allocations?.[0]?.grade) ?? '—';
          const formattedDate = order.created_at ? order.created_at.split('T')[0] : '—';

          return (
            <Card key={order.id} glow={order.status === 'disputed' || order.dispute_status === 'open_for_review'}>
              <View style={styles.orderTop}>
                <View style={{ flex: 1, marginRight: 8 }}>
                  <Text style={styles.orderIdText} numberOfLines={1}>{t.orderId} {order.id}</Text>
                  <Text style={styles.buyerNameText} numberOfLines={1}>Buyer: {order.buyer_id || 'Direct Wholesale'}</Text>
                  {order.allocations && order.allocations.length > 0 && (
                    <Text style={{ fontSize: 11, color: COLORS.textMuted }}>
                      {order.allocations.length} {lang === 'bn' ? 'কৃষকের বরাদ্দ' : 'farmer allocation(s)'}
                    </Text>
                  )}
                </View>
                {getStatusBadge(order.status)}
              </View>

              <View style={styles.orderSpecsRow}>
                <View style={styles.specBox}>
                  <Text style={styles.specLabel}>{t.crop}</Text>
                  <Text style={styles.specVal}>{(order.crop || 'crop').toUpperCase()}</Text>
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

            {evidenceLoading ? (
              <ActivityIndicator size="large" color={COLORS.cyan} style={{ padding: 40 }} />
            ) : evidenceError ? (
              <View style={{ padding: 24, alignItems: 'center' }}>
                <Ionicons name="alert-circle-outline" size={40} color={COLORS.warningOrange} />
                <Text style={{ color: COLORS.textPrimary, fontSize: 14, textAlign: 'center', marginTop: 12 }}>
                  {evidenceError}
                </Text>
              </View>
            ) : selectedEvidence ? (
              <ScrollView>
                <Text style={styles.evSub}>
                  {lang === 'bn'
                    ? 'কৃষকের পূর্ব-বিক্রয় রেকর্ড বনাম বায়ারের ডেলিভারি পর্যবেক্ষণ'
                    : 'Pre-sale verified batch vs Delivery observation'}
                </Text>

                {/* Side-by-Side comparison cards */}
                <View style={styles.compareRow}>
                  {/* Farmer Record (pre_sale) */}
                  <View style={styles.compareCol}>
                    <Text style={styles.colTitle}>👨‍🌾 {lang === 'bn' ? 'পূর্ব-বিক্রয় রেকর্ড' : 'Pre-sale Record'}</Text>
                    <Text style={styles.evField}>
                      {t.grade}: <Text style={{ color: COLORS.neonGreen, fontWeight: '700' }}>{selectedEvidence.pre_sale?.grade || '—'}</Text>
                    </Text>
                    <Text style={styles.evField}>
                      {t.quantity}: {selectedEvidence.pre_sale?.weight_kg ?? '—'} kg
                    </Text>
                    <Text style={styles.evField}>
                      {lang === 'bn' ? 'দর:' : 'Price:'} ৳{selectedEvidence.pre_sale?.agreed_price ?? '—'}
                    </Text>
                    <Badge
                      label={selectedEvidence.pre_sale?.photo_recorded ? 'Photo Verified' : 'No Photo'}
                      variant={selectedEvidence.pre_sale?.photo_recorded ? 'green' : 'orange'}
                      style={{ marginTop: 8 }}
                    />
                  </View>

                  {/* Buyer Report (at_delivery) */}
                  <View style={styles.compareCol}>
                    <Text style={styles.colTitle}>🏢 {lang === 'bn' ? 'ডেলিভারিতে পর্যবেক্ষণ' : 'At Delivery'}</Text>
                    <Text style={styles.evField}>
                      {t.grade}: <Text style={{ color: COLORS.warningOrange, fontWeight: '700' }}>{selectedEvidence.at_delivery?.grade || '—'}</Text>
                    </Text>
                    <Text style={styles.evField}>
                      {t.quantity}: {selectedEvidence.at_delivery?.weight_kg ?? '—'} kg
                    </Text>
                    <Text style={styles.evField}>
                      {lang === 'bn' ? 'দাবীকৃত ছাড়:' : 'Deduction:'} {selectedEvidence.at_delivery?.proposed_deduction_pct ?? 0}%
                    </Text>
                    {selectedEvidence.at_delivery?.reason ? (
                      <Text style={[styles.evField, { fontSize: 11, color: COLORS.textMuted, marginTop: 4 }]}>
                        {selectedEvidence.at_delivery.reason}
                      </Text>
                    ) : null}
                  </View>
                </View>

                {/* Discrepancies */}
                {selectedEvidence.discrepancies && selectedEvidence.discrepancies.length > 0 && (
                  <Card glow style={{ marginTop: 14 }}>
                    <Text style={styles.aiRecTitle}>⚠️ {lang === 'bn' ? 'অসঙ্গতিসমূহ (Discrepancies):' : 'Discrepancies:'}</Text>
                    {selectedEvidence.discrepancies.map((d, i) => (
                      <Text key={i} style={[styles.aiRecText, { color: COLORS.warningOrange, marginBottom: 4 }]}>
                        • {d}
                      </Text>
                    ))}
                  </Card>
                )}

                {/* Notes */}
                {selectedEvidence.notes && selectedEvidence.notes.length > 0 && (
                  <Card style={{ marginTop: 10 }}>
                    <Text style={styles.aiRecTitle}>📝 {lang === 'bn' ? 'পর্যবেক্ষণ নোট (Notes):' : 'Notes:'}</Text>
                    {selectedEvidence.notes.map((n, i) => (
                      <Text key={i} style={[styles.aiRecText, { marginBottom: 4 }]}>
                        • {n}
                      </Text>
                    ))}
                  </Card>
                )}

                {/* Neutral Statement */}
                {selectedEvidence.statement ? (
                  <Card style={{ marginTop: 10, backgroundColor: 'rgba(0, 242, 254, 0.05)' }}>
                    <Text style={[styles.aiRecText, { fontStyle: 'italic', color: COLORS.cyan }]}>
                      {selectedEvidence.statement}
                    </Text>
                  </Card>
                ) : null}
              </ScrollView>
            ) : null}
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
