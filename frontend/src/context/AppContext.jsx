import { createContext, useState, useCallback, useRef, useMemo, useEffect } from 'react';
import * as api from '@/utils/api';

export const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [pedidos, setPedidos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [session, setSession] = useState(null);
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adminViewAs, setAdminViewAs] = useState(null); // admin role switcher
  const toastTimer = useRef(null);

  const showToast = useCallback((msg, type = 'success') => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ msg, type });
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  }, []);

  // ── Auth: handle OAuth callback + session restore ──────────

  useEffect(() => {
    const init = async () => {
      const params = new URLSearchParams(window.location.search);
      const tokenFromUrl = params.get('token');

      if (tokenFromUrl) {
        window.history.replaceState({}, document.title, '/');
        try {
          const user = await api.handleOAuthCallback(tokenFromUrl);
          setSession({ token: tokenFromUrl, user });
        } catch (e) {
          showToast('Error al iniciar sesión: ' + e.message, 'error');
        }
        setLoading(false);
        return;
      }

      try {
        const user = await api.restoreSession();
        if (user) {
          setSession({ token: api.getStoredToken(), user });
        }
      } catch {
        // Token invalid, session cleared by restoreSession
      }
      setLoading(false);
    };

    init();
  }, [showToast]);

  // ── Data loading ───────────────────────────────────────────

  const loadPedidos = useCallback(async () => {
    try {
      const data = await api.fetchPedidos();
      setPedidos(data);
    } catch (e) { showToast(e.message, 'error'); }
  }, [showToast]);

  const loadUsuarios = useCallback(async () => {
    try {
      const data = await api.fetchUsuarios();
      setUsuarios(data);
    } catch { /* admin only, ignore for other roles */ }
  }, []);

  // ── Auth actions ───────────────────────────────────────────

  const loginMicrosoft = useCallback(() => {
    api.loginMicrosoft();
  }, []);

  const logout = useCallback(() => {
    api.logout();
    setSession(null);
    setPedidos([]);
    setUsuarios([]);
  }, []);

  // Load pedidos when session is established
  useEffect(() => {
    if (session) loadPedidos();
  }, [session, loadPedidos]);

  // ── Context value ──────────────────────────────────────────

  const ctx = useMemo(
    () => ({
      pedidos, setPedidos, usuarios,
      session, loginMicrosoft, logout, showToast, toast, loading,
      loadPedidos, loadUsuarios,
      adminViewAs, setAdminViewAs,
    }),
    [pedidos, usuarios, session, loginMicrosoft, logout, showToast, toast, loading, loadPedidos, loadUsuarios, adminViewAs]
  );

  return <AppContext.Provider value={ctx}>{children}</AppContext.Provider>;
}
