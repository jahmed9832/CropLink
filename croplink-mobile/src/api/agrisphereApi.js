import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Auto-detect PC IP from Expo packager host
const debuggerHost = Constants.expoConfig?.hostUri || Constants.manifest2?.extra?.expoGo?.debuggerHost || '';
const localIp = debuggerHost ? debuggerHost.split(':')[0] : '192.168.0.106';

export const LOCAL_SERVER_URL = `http://${localIp}:8000`;
export const RENDER_SERVER_URL = 'https://agrisphere-backend-vb4o.onrender.com';

// In standalone APK build (where anyone installs it), default to Render cloud
export const DEFAULT_SERVER_URL = (typeof __DEV__ !== 'undefined' && __DEV__ && debuggerHost)
  ? LOCAL_SERVER_URL
  : RENDER_SERVER_URL;

const SERVER_URL_KEY = '@croplink_server_url';
const TIMEOUT_MS = 65000;
const TOKEN_KEY = '@croplink_token';
const USER_KEY = '@croplink_user';
const LANG_KEY = '@croplink_lang';

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

class AgriSphereApi {
  constructor() {
    this.baseUrl = DEFAULT_SERVER_URL;
    this.token = null;
    this.lang = 'bn';
    this.isServerAwake = false;
    this.isWakingUp = false;
  }

  async init() {
    try {
      const [savedToken, savedLang, savedUrl] = await Promise.all([
        AsyncStorage.getItem(TOKEN_KEY),
        AsyncStorage.getItem(LANG_KEY),
        AsyncStorage.getItem(SERVER_URL_KEY),
      ]);
      if (savedToken) this.token = savedToken;
      if (savedLang) this.lang = savedLang;
      if (savedUrl) {
        this.baseUrl = savedUrl;
      } else {
        this.baseUrl = DEFAULT_SERVER_URL;
      }
    } catch (_) {}

    // Instant proactive wake-up call to backend in background
    this.wakeUpServer();
  }

  async setServerUrl(url) {
    this.baseUrl = url.replace(/\/+$/, '');
    await AsyncStorage.setItem(SERVER_URL_KEY, this.baseUrl);
    this.isServerAwake = false;
    this.wakeUpServer();
  }

  setLang(lang) {
    this.lang = lang;
    AsyncStorage.setItem(LANG_KEY, lang).catch(() => {});
  }

  async wakeUpServer(onStatusChange) {
    if (this.isServerAwake || this.isWakingUp) return;
    this.isWakingUp = true;
    if (onStatusChange) onStatusChange('waking');

    try {
      const res = await this.health();
      if (res && res.status === 'ok') {
        this.isServerAwake = true;
        this.isWakingUp = false;
        if (onStatusChange) onStatusChange('active');
        return true;
      }
    } catch (_) {
      this.isWakingUp = false;
      if (onStatusChange) onStatusChange('offline');
      return false;
    }
  }

  async request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Accept-Language': this.lang,
      ...(options.headers || {}),
    };

    if (this.token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const isFormData = Boolean(
      options.body && (
        options.body instanceof FormData ||
        typeof options.body.append === 'function' ||
        options.body._parts ||
        Object.prototype.toString.call(options.body) === '[object FormData]'
      )
    );

    if (isFormData) {
      delete headers['Content-Type'];
    } else if (!headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const res = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const contentType = res.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        data = await res.text();
      }

      if (!res.ok) {
        let msg = 'Request failed';
        if (data && data.detail) {
          msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
        throw new ApiError(res.status, msg);
      }

      // If successful, we know the server is awake
      this.isServerAwake = true;
      return data;
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new ApiError(0, 'Server is taking longer to respond. It may be waking up, please retry.');
      }
      throw err;
    }
  }

  // Health
  health() {
    return this.request('/health', { method: 'GET' });
  }

  // Auth
  async register({ name, phone, password, role = 'farmer', district = 'Gazipur' }) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, phone, password, role, district }),
    });
    if (data.token) {
      this.token = data.token;
      await AsyncStorage.setItem(TOKEN_KEY, data.token);
      await AsyncStorage.setItem(USER_KEY, JSON.stringify(data));
    }
    return data;
  }

  async login({ phone, password }) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ phone, password }),
    });
    if (data.token) {
      this.token = data.token;
      await AsyncStorage.setItem(TOKEN_KEY, data.token);
      try {
        const me = await this.request('/auth/me');
        if (me && me.profile) {
          data.profile = me.profile;
        }
        if (me && me.user_id) {
          data.user_id = me.user_id;
        }
        if (me && me.role) {
          data.role = me.role;
        }
      } catch (_) {}
      await AsyncStorage.setItem(USER_KEY, JSON.stringify(data));
    }
    return data;
  }

  async logout() {
    this.token = null;
    await AsyncStorage.removeItem(TOKEN_KEY);
    await AsyncStorage.removeItem(USER_KEY);
  }

  async getSavedUser() {
    try {
      const userStr = await AsyncStorage.getItem(USER_KEY);
      return userStr ? JSON.parse(userStr) : null;
    } catch (_) {
      return null;
    }
  }

  // Dashboard
  getFarmerDashboard(farmerId) {
    return this.request(`/dashboard/farmer/${farmerId}`);
  }

  getBuyerDashboard(buyerId) {
    return this.request(`/dashboard/buyer/${buyerId}`);
  }

  // Prices & Forecast
  getTodayPrices(market = '') {
    const query = market ? `?market=${encodeURIComponent(market)}` : '';
    return this.request(`/prices/today${query}`);
  }

  getPriceHistory(crop, market = 'Dhaka', days = 30) {
    return this.request(`/prices/history?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}&days=${days}`);
  }

  getForecast(crop, market = 'Dhaka') {
    return this.request(`/forecast?crop=${encodeURIComponent(crop)}&market=${encodeURIComponent(market)}`);
  }

  // Core Decision Engine
  decide(payload) {
    return this.request('/decision/net-profit', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Direct Base64 Photo Grading (/grade-json) - 100% reliable across all Android & iOS devices
  async gradePhotoBase64(base64Data, crop = 'tomato') {
    return this.request('/grade-json', {
      method: 'POST',
      body: JSON.stringify({
        photo_base64: base64Data,
        crop: crop,
      }),
    });
  }

  // Direct fast photo grading (/grade)
  async gradePhotoOnly(uri) {
    const formData = new FormData();
    const cleanUri = Platform.OS === 'android' ? uri : uri.replace('file://', '');
    formData.append('file', {
      uri: cleanUri,
      name: 'produce.jpg',
      type: 'image/jpeg',
    });

    return this.request('/grade', {
      method: 'POST',
      body: formData,
    });
  }

  // Photo Grading & Batch creation (/batches/from-photo)
  async gradePhotoFromUri(uri, crop = 'tomato', quantityKg = 500, district = 'Gazipur', farmerId = null) {
    const formData = new FormData();
    const cleanUri = Platform.OS === 'android' ? uri : uri.replace('file://', '');
    const filename = uri.split('/').pop() || 'produce.jpg';

    formData.append('file', {
      uri: cleanUri,
      name: filename.includes('.') ? filename : 'produce.jpg',
      type: 'image/jpeg',
    });
    formData.append('crop', crop);
    formData.append('quantity_kg', String(quantityKg));
    formData.append('district', district);
    if (farmerId) {
      formData.append('farmer_id', farmerId);
    }

    return this.request('/batches/from-photo', {
      method: 'POST',
      body: formData,
    });
  }

  getBatchPassport(batchId) {
    return this.request(`/batches/${batchId}/passport`);
  }

  // Lots & Demands
  getLots(farmerId = null) {
    const q = farmerId ? `?farmer_id=${encodeURIComponent(farmerId)}` : '';
    return this.request(`/lots${q}`);
  }

  createLot(payload) {
    return this.request('/lots', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  getOffersForLot(lotId) {
    return this.request(`/lots/${lotId}/offers`);
  }

  getDemands(buyerId = null) {
    const q = buyerId ? `?buyer_id=${encodeURIComponent(buyerId)}` : '';
    return this.request(`/demands${q}`);
  }

  createDemand(payload) {
    return this.request('/demands', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Pooling
  createPoolPlan(demandId) {
    return this.request('/pool/plan', {
      method: 'POST',
      body: JSON.stringify({ demand_id: demandId }),
    });
  }

  setBaseUrl(url) {
    this.baseUrl = url.replace(/\/+$/, '');
    this.isServerAwake = false;
    this.wakeUpServer();
  }

  // AI Assistant & Voice Negotiation
  askAssistant(message, context = {}) {
    return this.request('/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({
        text: message,
        message: message,
        market: context.market || 'Dhaka',
        ...context,
      }),
    });
  }

  draftCounterOffer(payload) {
    return this.request('/negotiation/counter-offer', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Orders & Dispute
  getOrders() {
    return this.request('/orders');
  }

  recordDelivery(orderId, payload) {
    return this.request(`/orders/${orderId}/delivery`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  getDisputeEvidence(orderId) {
    return this.request(`/orders/${orderId}/evidence`);
  }

  getAlerts(farmerId) {
    return this.request(`/alerts/farmer/${farmerId}`);
  }
}

export const api = new AgriSphereApi();
export default api;
