import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/agrisphereApi';
import { TRANSLATIONS } from '../constants/translations';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState('bn');
  const [serverStatus, setServerStatus] = useState('waking'); // 'waking' | 'active' | 'offline'

  useEffect(() => {
    async function loadInitialData() {
      await api.init();
      setLang(api.lang);

      // Check saved user session
      const savedUser = await api.getSavedUser();
      if (savedUser) {
        setUser(savedUser);
      }
      setLoading(false);

      // Trigger server wake-up check immediately
      api.wakeUpServer((status) => {
        setServerStatus(status);
      });
    }

    loadInitialData();
  }, []);

  const toggleLanguage = () => {
    const newLang = lang === 'bn' ? 'en' : 'bn';
    setLang(newLang);
    api.setLang(newLang);
  };

  const login = async (phone, password) => {
    const result = await api.login({ phone, password });
    setUser(result);
    setServerStatus('active');
    return result;
  };

  const register = async (userData) => {
    const result = await api.register(userData);
    setUser(result);
    setServerStatus('active');
    return result;
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  const [serverUrl, setServerUrl] = useState(api.baseUrl);

  const switchServerUrl = async (newUrl) => {
    await api.setServerUrl(newUrl);
    setServerUrl(api.baseUrl);
  };

  const t = TRANSLATIONS[lang] || TRANSLATIONS.bn;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        lang,
        t,
        serverStatus,
        serverUrl,
        switchServerUrl,
        toggleLanguage,
        login,
        register,
        logout,
        refreshServerStatus: () => api.wakeUpServer(setServerStatus),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
