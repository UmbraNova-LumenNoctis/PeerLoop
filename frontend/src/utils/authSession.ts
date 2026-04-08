import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { jwtDecode } from "jwt-decode";

interface JwtPayload {
  exp?: number;
}

export const AUTH_TOKEN_UPDATED_EVENT = "auth-token-updated";
export const AUTH_LOGOUT_EVENT = "auth-logout";

const AUTH_TOKEN_STORAGE_KEY = "token";
const REFRESH_ENDPOINT_PATH = "/api/auth/refresh";
const LOGIN_ENDPOINT_PATH = "/api/auth/login";
const SESSION_EXCHANGE_ENDPOINT_PATH = "/api/auth/session/exchange";
const EXPIRY_GRACE_SECONDS = 20;

let refreshTokenPromise: Promise<string | null> | null = null;

export const resolveApiBaseUrl = (): string => {
  const configuredUrl: string | undefined = import.meta.env.VITE_API_SERVER_URL;
  if (configuredUrl && configuredUrl.trim().length > 0) {
    return configuredUrl.trim();
  }

  if (typeof window !== "undefined") {
    const { origin, port } = window.location;
    if (port === "3000" || port === "5173") {
      const gatewayUrl = new URL(origin);
      gatewayUrl.protocol = "https:";
      gatewayUrl.port = "8443";
      return gatewayUrl.origin;
    }

    return origin;
  }

  return "https://localhost:8443";
};

const dispatchAuthEvent = (eventName: string): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(eventName));
};

export const getStoredToken = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }

  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (!token || !token.trim()) {
    return null;
  }

  return token.trim();
};

export const setStoredToken = (token: string, options?: { emitEvent?: boolean }): void => {
  if (typeof window === "undefined") {
    return;
  }

  const normalizedToken = (token || "").trim();
  if (!normalizedToken) {
    return;
  }

  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, normalizedToken);
  if (options?.emitEvent !== false) {
    dispatchAuthEvent(AUTH_TOKEN_UPDATED_EVENT);
  }
};

export const clearStoredToken = (options?: { emitEvent?: boolean }): void => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  if (options?.emitEvent !== false) {
    dispatchAuthEvent(AUTH_LOGOUT_EVENT);
  }
};

export const isTokenExpired = (token: string | null | undefined): boolean => {
  const normalizedToken = (token || "").trim();
  if (!normalizedToken) {
    return true;
  }

  try {
    const decoded = jwtDecode<JwtPayload>(normalizedToken);
    if (!decoded || typeof decoded.exp !== "number") {
      return false;
    }

    const currentEpochSeconds = Math.floor(Date.now() / 1000);
    return decoded.exp <= currentEpochSeconds + EXPIRY_GRACE_SECONDS;
  } catch {
    return true;
  }
};

const extractAccessToken = (data: unknown): string | null => {
  if (!data || typeof data !== "object") {
    return null;
  }

  const value = (data as Record<string, unknown>).access_token;
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }

  return value.trim();
};

export const refreshAccessToken = async (): Promise<string | null> => {
  if (refreshTokenPromise) {
    return refreshTokenPromise;
  }

  refreshTokenPromise = (async () => {
    try {
      const response = await axios.post(
        `${resolveApiBaseUrl()}${REFRESH_ENDPOINT_PATH}`,
        {},
        {
          withCredentials: true,
          timeout: 10000,
        },
      );

      const nextToken = extractAccessToken(response.data);
      if (!nextToken) {
        clearStoredToken();
        return null;
      }

      setStoredToken(nextToken);
      return nextToken;
    } catch {
      clearStoredToken();
      return null;
    } finally {
      refreshTokenPromise = null;
    }
  })();

  return refreshTokenPromise;
};

export const ensureAccessToken = async (): Promise<string | null> => {
  const currentToken = getStoredToken();
  if (!currentToken) {
    return null;
  }

  if (!isTokenExpired(currentToken)) {
    return currentToken;
  }

  return refreshAccessToken();
};

const shouldSkipRefresh = (requestUrl?: string): boolean => {
  if (!requestUrl) {
    return false;
  }

  return requestUrl.includes(REFRESH_ENDPOINT_PATH)
    || requestUrl.includes(LOGIN_ENDPOINT_PATH)
    || requestUrl.includes(SESSION_EXCHANGE_ENDPOINT_PATH);
};

export const attachAuthInterceptors = (httpClient: AxiosInstance): void => {
  httpClient.interceptors.request.use(
    async (config: InternalAxiosRequestConfig): Promise<InternalAxiosRequestConfig> => {
      if (shouldSkipRefresh(config.url)) {
        return config;
      }

      const token = await ensureAccessToken();
      if (!token) {
        return config;
      }

      config.headers = config.headers || {};
      (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
      return config;
    },
    (error: AxiosError) => Promise.reject(error),
  );

  httpClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const statusCode = error.response?.status;
      const requestConfig = (error.config || {}) as InternalAxiosRequestConfig & { _authRetried?: boolean };

      if (
        statusCode !== 401
        || requestConfig._authRetried
        || shouldSkipRefresh(requestConfig.url)
      ) {
        return Promise.reject(error);
      }

      requestConfig._authRetried = true;
      const refreshedToken = await refreshAccessToken();
      if (!refreshedToken) {
        return Promise.reject(error);
      }

      requestConfig.headers = requestConfig.headers || {};
      (requestConfig.headers as Record<string, string>).Authorization = `Bearer ${refreshedToken}`;
      return httpClient(requestConfig);
    },
  );
};
