// The API URL mirrors RENDER_SERVER_URL in croplink-mobile/src/api/agrisphereApi.js.
export const API_URL = (import.meta.env.VITE_API_URL || 'https://agrisphere-backend-sv5x.onrender.com').replace(/\/+$/, '');

export const ROUTES = {
  login: '/login',
  register: '/register',
};
