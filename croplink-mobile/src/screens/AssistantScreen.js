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
  Clipboard,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { COLORS } from '../constants/theme';
import Card from '../components/Card';
import Badge from '../components/Badge';
import GradientButton from '../components/GradientButton';
import api from '../api/agrisphereApi';

export default function AssistantScreen() {
  const { t, lang } = useAuth();
  const [activeTab, setActiveTab] = useState('assistant'); // 'assistant' | 'negotiation'

  // Chat State
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text:
        lang === 'bn'
          ? 'আসসালামু আলাইকুম! আমি ক্রপলিংক সহকারী। আপনি আমাকে বাজার দর, ফসল বিক্রি করার সিদ্ধান্ত বা ঝুঁকি সম্পর্কে বাংলায় যে কোনো প্রশ্ন করতে পারেন।'
          : 'Hello! I am your CropLink Assistant. Ask me anything about crop prices, selling decisions, or post-harvest protection.',
    },
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  // Negotiation Draft State
  const [negCrop, setNegCrop] = useState('tomato');
  const [negQty, setNegQty] = useState('500');
  const [prodCost, setProdCost] = useState('45');
  const [buyerOffer, setBuyerOffer] = useState('50');
  const [draftResult, setDraftResult] = useState(null);
  const [draftLoading, setDraftLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || chatLoading) return;
    const userMsg = inputMessage.trim();
    setInputMessage('');
    setMessages((prev) => [...prev, { sender: 'user', text: userMsg }]);
    setChatLoading(true);

    try {
      const res = await api.askAssistant(userMsg);
      const reply = res.reply || res.message || (lang === 'bn' ? 'তথ্য পাওয়া গেছে।' : 'Response received.');
      setMessages((prev) => [...prev, { sender: 'bot', text: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text:
            err.message ||
            (lang === 'bn'
              ? 'সার্ভার থেকে উত্তর পাওয়া যায়নি। দয়া করে আবার চেষ্টা করুন।'
              : 'Could not connect to assistant. Please try again.'),
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleGenerateDraft = async () => {
    setDraftLoading(true);
    setDraftResult(null);
    try {
      const bOffer = parseFloat(buyerOffer) || 50;
      const res = await api.draftCounterOffer({
        crop: negCrop,
        quantity_kg: parseFloat(negQty) || 500,
        production_cost_per_kg: parseFloat(prodCost) || 45,
        offers: [{ price_per_kg: bOffer }],
      });
      setDraftResult(res);
    } catch (err) {
      Alert.alert(
        lang === 'bn' ? 'দর কষাকষি সহায়িকা ত্রুটি' : 'Negotiation Error',
        err.message || (lang === 'bn' ? 'কাউন্টার অফার তৈরি করা সম্ভব হয়নি।' : 'Failed to draft counter offer.')
      );
    } finally {
      setDraftLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    if (Clipboard && Clipboard.setString) {
      Clipboard.setString(text);
      Alert.alert(lang === 'bn' ? 'কপি হয়েছে' : 'Copied', lang === 'bn' ? 'বার্তাটি ক্লিপবোর্ডে কপি করা হয়েছে।' : 'Draft copied to clipboard.');
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <View style={styles.topContent}>
        {/* Tab Switcher */}
        <View style={styles.tabBar}>
          <TouchableOpacity
            onPress={() => setActiveTab('assistant')}
            style={[styles.tabBtn, activeTab === 'assistant' && styles.tabBtnActive]}
          >
            <Ionicons
              name="chatbubbles-outline"
              size={16}
              color={activeTab === 'assistant' ? COLORS.cyan : COLORS.textMuted}
            />
            <Text
              style={[styles.tabText, activeTab === 'assistant' && styles.tabTextActive]}
            >
              {t.assistantTitle}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setActiveTab('negotiation')}
            style={[styles.tabBtn, activeTab === 'negotiation' && styles.tabBtnActive]}
          >
            <Ionicons
              name="pricetags-outline"
              size={16}
              color={activeTab === 'negotiation' ? COLORS.cyan : COLORS.textMuted}
            />
            <Text
              style={[styles.tabText, activeTab === 'negotiation' && styles.tabTextActive]}
            >
              {t.negotiationTitle}
            </Text>
          </TouchableOpacity>
        </View>

        {activeTab === 'assistant' ? (
          /* Assistant Chat Tab */
          <View style={styles.chatWrapper}>
            <ScrollView
              style={styles.chatScroll}
              contentContainerStyle={{ padding: 16, paddingBottom: 20 }}
            >
              {messages.map((m, idx) => (
                <View
                  key={idx}
                  style={[
                    styles.msgBubble,
                    m.sender === 'user' ? styles.userBubble : styles.botBubble,
                  ]}
                >
                  <Text
                    style={[
                      styles.msgText,
                      m.sender === 'user' ? styles.userMsgText : styles.botMsgText,
                    ]}
                  >
                    {m.text}
                  </Text>
                </View>
              ))}
              {chatLoading && (
                <View style={[styles.msgBubble, styles.botBubble]}>
                  <Text style={styles.botMsgText}>
                    {lang === 'bn' ? 'সহকারী উত্তর লিখছে...' : 'CropLink AI typing...'}
                  </Text>
                </View>
              )}
            </ScrollView>

            {/* Quick 1-Tap Agricultural Question Chips */}
            <View style={styles.quickChipsBox}>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickChipsContent}>
                {[
                  lang === 'bn' ? 'আলুর দাম কেমন থাকবে?' : 'Potato price outlook?',
                  'Alu koto kore bikri korbo?',
                  lang === 'bn' ? 'টমেটোর পাতায় হলুদ দাগ কেন?' : 'Yellow spots on tomato?',
                  lang === 'bn' ? '৫০০ কেজি ফসল এখন বেচব না অপেক্ষা করব?' : 'Sell now or wait 7d?',
                ].map((txt, i) => (
                  <TouchableOpacity
                    key={i}
                    style={styles.quickChip}
                    onPress={() => {
                      setInputMessage(txt);
                    }}
                    activeOpacity={0.7}
                  >
                    <Ionicons name="sparkles-outline" size={12} color="#10B981" />
                    <Text style={styles.quickChipText}>{txt}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>

            {/* Input Bar */}
            <View style={styles.inputBar}>
              <TextInput
                style={styles.chatInput}
                placeholder={lang === 'bn' ? 'বাংলা বা Banglish-এ প্রশ্ন করুন...' : 'Ask in Bengali, Banglish or English...'}
                placeholderTextColor={COLORS.textMuted}
                value={inputMessage}
                onChangeText={setInputMessage}
                onSubmitEditing={handleSendMessage}
              />
              <TouchableOpacity
                onPress={handleSendMessage}
                style={styles.sendBtn}
                activeOpacity={0.8}
              >
                <Ionicons name="arrow-up" size={20} color="#06121E" />
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          /* Negotiation Counter-Offer Tab */
          <ScrollView contentContainerStyle={styles.negContent}>
            <Card glow>
              <Text style={styles.negHeaderTitle}>{t.negotiationTitle}</Text>
              <Text style={styles.negHeaderSub}>{t.negotiationSub}</Text>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>{t.productionCost}</Text>
                <TextInput
                  style={styles.input}
                  keyboardType="numeric"
                  value={prodCost}
                  onChangeText={setProdCost}
                  placeholder="45"
                  placeholderTextColor={COLORS.textMuted}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>{t.buyerOffer}</Text>
                <TextInput
                  style={styles.input}
                  keyboardType="numeric"
                  value={buyerOffer}
                  onChangeText={setBuyerOffer}
                  placeholder="50"
                  placeholderTextColor={COLORS.textMuted}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>{t.quantity}</Text>
                <TextInput
                  style={styles.input}
                  keyboardType="numeric"
                  value={negQty}
                  onChangeText={setNegQty}
                  placeholder="500"
                  placeholderTextColor={COLORS.textMuted}
                />
              </View>

              <GradientButton
                title={t.generateCounter}
                onPress={handleGenerateDraft}
                loading={draftLoading}
                style={{ marginTop: 10 }}
              />
            </Card>

            {/* Draft Output */}
            {draftResult && (
              <Card glow style={{ marginTop: 16 }}>
                <View style={styles.draftTop}>
                  <Text style={styles.draftPriceLabel}>{t.minPrice}</Text>
                  <Text style={styles.draftPriceVal}>
                    ৳{draftResult.minimum_acceptable_price_per_kg ?? '—'} / kg
                  </Text>
                </View>

                {draftResult.offers && draftResult.offers[0] && (
                  <View style={{ marginTop: 8 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text style={{ color: COLORS.textMuted, fontSize: 13 }}>
                        {lang === 'bn' ? 'প্রস্তাবিত অ্যাকশন:' : 'Action:'}
                      </Text>
                      <Badge
                        label={draftResult.offers[0].action === 'accept' ? 'Accept Offer' : 'Counter Offer'}
                        variant={draftResult.offers[0].action === 'accept' ? 'green' : 'orange'}
                      />
                    </View>
                    {draftResult.offers[0].suggested_counter_price && draftResult.offers[0].action !== 'accept' && (
                      <Text style={{ color: COLORS.cyan, fontWeight: '700', fontSize: 14, marginTop: 4 }}>
                        {lang === 'bn' ? 'প্রস্তাবিত পাল্টা দর:' : 'Suggested Counter:'} ৳{draftResult.offers[0].suggested_counter_price}/kg
                      </Text>
                    )}
                  </View>
                )}

                <View style={styles.draftBox}>
                  <Text style={styles.draftBoxHeader}>📝 {t.draftMessage}</Text>
                  <Text style={styles.draftBodyText}>
                    {lang === 'bn'
                      ? (draftResult.offers?.[0]?.draft_message_bn || draftResult.offers?.[0]?.draft_message || '')
                      : (draftResult.offers?.[0]?.draft_message_en || draftResult.offers?.[0]?.draft_message || '')}
                  </Text>
                </View>

                <TouchableOpacity
                  onPress={() =>
                    copyToClipboard(
                      lang === 'bn'
                        ? (draftResult.offers?.[0]?.draft_message_bn || draftResult.offers?.[0]?.draft_message || '')
                        : (draftResult.offers?.[0]?.draft_message_en || draftResult.offers?.[0]?.draft_message || '')
                    )
                  }
                  style={styles.copyBtn}
                >
                  <Ionicons name="copy-outline" size={16} color={COLORS.cyan} />
                  <Text style={styles.copyBtnText}>{t.copyMessage}</Text>
                </TouchableOpacity>
              </Card>
            )}
          </ScrollView>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
  },
  topContent: {
    flex: 1,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: COLORS.bgCardSolid,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.borderLight,
    paddingHorizontal: 12,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 14,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabBtnActive: {
    borderBottomColor: COLORS.cyan,
  },
  tabText: {
    color: COLORS.textMuted,
    fontSize: 13,
    fontWeight: '600',
  },
  tabTextActive: {
    color: COLORS.cyan,
  },
  chatWrapper: {
    flex: 1,
  },
  chatScroll: {
    flex: 1,
  },
  msgBubble: {
    maxWidth: '82%',
    padding: 14,
    borderRadius: 16,
    marginBottom: 12,
  },
  botBubble: {
    alignSelf: 'flex-start',
    backgroundColor: COLORS.bgCard,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    borderBottomLeftRadius: 4,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#0F2E23',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
    borderBottomRightRadius: 4,
  },
  msgText: {
    fontSize: 14,
    lineHeight: 21,
  },
  botMsgText: {
    color: COLORS.textPrimary,
  },
  userMsgText: {
    color: '#ECFDF5',
  },
  quickChipsBox: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: COLORS.bgDark,
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
  },
  quickChipsContent: {
    flexDirection: 'row',
    gap: 8,
  },
  quickChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.22)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  quickChipText: {
    fontSize: 12,
    color: '#34D399',
    fontWeight: '600',
  },
  inputBar: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: COLORS.bgCardSolid,
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
    gap: 10,
    alignItems: 'center',
  },
  chatInput: {
    flex: 1,
    backgroundColor: COLORS.bgInput,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    color: COLORS.textPrimary,
    fontSize: 13.5,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
  },
  sendBtn: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#10B981',
    alignItems: 'center',
    justifyContent: 'center',
  },
  negContent: {
    padding: 16,
    paddingBottom: 40,
  },
  negHeaderTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.textPrimary,
  },
  negHeaderSub: {
    fontSize: 12,
    color: COLORS.textMuted,
    marginTop: 4,
    marginBottom: 14,
  },
  inputGroup: {
    marginBottom: 12,
  },
  inputLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    fontWeight: '600',
    marginBottom: 6,
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
  draftTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  draftPriceLabel: {
    fontSize: 13,
    color: COLORS.textMuted,
  },
  draftPriceVal: {
    fontSize: 18,
    fontWeight: '800',
    color: COLORS.cyan,
  },
  draftBox: {
    backgroundColor: 'rgba(0, 0, 0, 0.35)',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.borderLight,
    marginBottom: 12,
  },
  draftBoxHeader: {
    fontSize: 12,
    fontWeight: '700',
    color: COLORS.cyan,
    marginBottom: 6,
  },
  draftBodyText: {
    fontSize: 13,
    color: COLORS.textPrimary,
    lineHeight: 19,
  },
  copyBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.25)',
  },
  copyBtnText: {
    color: COLORS.cyan,
    fontSize: 13,
    fontWeight: '700',
  },
});
