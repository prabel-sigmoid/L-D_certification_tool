import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL;

// ── Token helpers ──────────────────────────────────────────────────────────

/**
 * Decode JWT payload (no signature verification — just reading claims).
 * JWT format: base64(header).base64(payload).signature
 */
function decodeTokenPayload(token) {
  try {
    const payloadB64 = token.split(".")[1];
    const padded = payloadB64.padEnd(
      payloadB64.length + ((4 - (payloadB64.length % 4)) % 4),
      "="
    );
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

/**
 * Returns true if a token exists in sessionStorage AND is not expired.
 */
export function isTokenValid() {
  const token = sessionStorage.getItem("token");
  if (!token) return false;
  const payload = decodeTokenPayload(token);
  if (!payload || !payload.exp) return false;
  // exp is in seconds; Date.now() is in ms
  return payload.exp * 1000 > Date.now();
}

/**
 * Get the stored token (session-scoped).
 */
export function getToken() {
  return sessionStorage.getItem("token");
}

// ── Auth actions ───────────────────────────────────────────────────────────

export const login = () => {
  window.location.href = `${API_URL}/auth/login`;
};

export const handleAuthCallback = async () => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (!token) return null;

  // Store in sessionStorage (tab-scoped — new tab = new session = login required)
  sessionStorage.setItem("token", token);

  // Clean the token from the URL bar without reloading
  window.history.replaceState({}, document.title, "/");

  return { access_token: token };
};

export const logout = () => {
  sessionStorage.removeItem("token");
  window.location.href = "/login";
};

// ── Axios interceptors ─────────────────────────────────────────────────────

// Attach token to every request
axios.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401 from any API call → clear session and redirect to login
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
