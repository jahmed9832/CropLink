import { API_URL } from '../config.js';

const KEY = 'croplink.session';

async function request(path, body) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept-Language': 'en' },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error('Could not reach the CropLink server. It may be waking up — please try again in a minute.');
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON response */
  }
  if (!res.ok) {
    const detail = data && data.detail;
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : null;
    throw new Error(msg || `Request failed (${res.status}).`);
  }
  return data;
}

function persist(data) {
  const session = { token: data.token, userId: data.user_id, role: data.role };
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    /* storage unavailable */
  }
  return session;
}

export async function login({ phone, password }) {
  return persist(await request('/auth/login', { phone, password }));
}

export async function register({ name, phone, password, role, district }) {
  return persist(await request('/auth/register', { name, phone, password, role, district: district || 'Dhaka' }));
}

export function getSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null');
  } catch {
    return null;
  }
}

export function logout() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
