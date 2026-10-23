import React, { useState } from 'react';
import {
  SafeAreaView,
  StatusBar,
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { AuthProvider, useAuth } from './src/context/AuthContext';
import { COLORS } from './src/constants/theme';
import Header from './src/components/Header';

// Screens
import LoginScreen from './src/screens/LoginScreen';
import DashboardScreen from './src/screens/DashboardScreen';
import DecisionScreen from './src/screens/DecisionScreen';
import GradingScreen from './src/screens/GradingScreen';
import MarketPricesScreen from './src/screens/MarketPricesScreen';
import AssistantScreen from './src/screens/AssistantScreen';
import PoolingScreen from './src/screens/PoolingScreen';
import OrdersScreen from './src/screens/OrdersScreen';

function MainApp() {
  const { user, loading, t, lang } = useAuth();
  const [currentTab, setCurrentTab] = useState('dashboard');

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.cyan} />
        <Text style={styles.loadingText}>CropLink</Text>
      </View>
    );
  }

  // If user not authenticated, show LoginScreen
  if (!user) {
    return <LoginScreen />;
  }

  const renderScreen = () => {
    switch (currentTab) {
      case 'dashboard':
        return <DashboardScreen onNavigate={(screen) => setCurrentTab(screen)} />;
      case 'decision':
        return <DecisionScreen />;
      case 'grading':
        return <GradingScreen />;
      case 'market':
        return <MarketPricesScreen />;
      case 'assistant':
        return <AssistantScreen />;
      case 'pooling':
        return <PoolingScreen />;
      case 'orders':
        return <OrdersScreen />;
      default:
        return <DashboardScreen onNavigate={(screen) => setCurrentTab(screen)} />;
    }
  };

  const navItems = [
    { id: 'dashboard', label: t.dashboard, icon: 'grid-outline', activeIcon: 'grid' },
    { id: 'decision', label: lang === 'bn' ? 'সিদ্ধান্ত' : 'Decide', icon: 'calculator-outline', activeIcon: 'calculator' },
    { id: 'grading', label: lang === 'bn' ? 'গ্রেডিং' : 'Grade', icon: 'camera-outline', activeIcon: 'camera' },
    { id: 'market', label: lang === 'bn' ? 'বাজার দর' : 'Market', icon: 'trending-up-outline', activeIcon: 'trending-up' },
    { id: 'assistant', label: lang === 'bn' ? 'সহকারী' : 'AI Help', icon: 'chatbubbles-outline', activeIcon: 'chatbubbles' },
    { id: 'orders', label: lang === 'bn' ? 'অর্ডার' : 'Orders', icon: 'receipt-outline', activeIcon: 'receipt' },
  ];

  const getScreenTitle = () => {
    switch (currentTab) {
      case 'decision':
        return lang === 'bn' ? 'সিদ্ধান্ত ইঞ্জিন' : 'Decision Engine';
      case 'grading':
        return lang === 'bn' ? 'ফটো গ্রেডিং ও QR' : 'Photo Grading & QR';
      case 'market':
        return lang === 'bn' ? 'বাজার দর ও পূর্বাভাস' : 'Market & Forecast';
      case 'assistant':
        return lang === 'bn' ? 'সহকারী ও দর-কষাকষি' : 'AI Assistant';
      case 'pooling':
        return lang === 'bn' ? 'সাপ্লাই পুলিং' : 'Supply Pooling';
      case 'orders':
        return lang === 'bn' ? 'অর্ডার ও রিপোর্ট' : 'Orders & Evidence';
      default:
        return 'CropLink';
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bgDark} />
      <Header
        title={getScreenTitle()}
        showBack={currentTab !== 'dashboard'}
        onBack={() => setCurrentTab('dashboard')}
      />

      <View style={styles.screenContainer}>{renderScreen()}</View>

      {/* Bottom Floating Navigation Bar */}
      <View style={styles.bottomNav}>
        {navItems.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <TouchableOpacity
              key={item.id}
              onPress={() => setCurrentTab(item.id)}
              style={styles.navTab}
              activeOpacity={0.7}
            >
              <Ionicons
                name={isActive ? item.activeIcon : item.icon}
                size={22}
                color={isActive ? COLORS.cyan : COLORS.textMuted}
              />
              <Text
                style={[
                  styles.navLabel,
                  isActive && styles.navLabelActive,
                ]}
                numberOfLines={1}
              >
                {item.label}
              </Text>
              {isActive && <View style={styles.activeIndicator} />}
            </TouchableOpacity>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 22,
    fontWeight: '900',
    color: COLORS.cyan,
    letterSpacing: 1,
  },
  screenContainer: {
    flex: 1,
  },
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: COLORS.bgCardSolid,
    borderTopWidth: 1,
    borderTopColor: COLORS.borderLight,
    paddingTop: 8,
    paddingBottom: 10,
    paddingHorizontal: 4,
    justifyContent: 'space-around',
  },
  navTab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 2,
    position: 'relative',
  },
  navLabel: {
    fontSize: 10,
    color: COLORS.textMuted,
    marginTop: 4,
    fontWeight: '600',
  },
  navLabelActive: {
    color: COLORS.cyan,
    fontWeight: '700',
  },
  activeIndicator: {
    position: 'absolute',
    bottom: -6,
    width: 16,
    height: 3,
    borderRadius: 2,
    backgroundColor: COLORS.cyan,
  },
});
