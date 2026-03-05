import React, { createContext, useContext, useState, useEffect } from 'react';

const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;

const AppContext = createContext(null);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
};

// Map de permisos requeridos por ruta
const ROUTE_PERMISSIONS = {
  '/dashboard': 'dashboard.ver',
  '/ventas': 'ventas.crear',
  '/delivery': 'delivery.ver',
  '/laboratorio': 'laboratorio.ver',
  '/productos': 'productos.ver',
  '/marcas': 'productos.ver',
  '/categorias': 'productos.ver',
  '/proveedores': 'proveedores.ver',
  '/clientes': 'clientes.ver',
  '/funcionarios': 'funcionarios.ver',
  '/stock': 'stock.ver',
  '/flota': 'flota.ver',
  '/facturas': 'facturas.ver',
  '/usuarios': 'usuarios.ver',
  '/permisos': 'usuarios.gestionar',
  '/sistema': 'sistema.configurar',
  '/historial-ventas': 'ventas.ver_historial',
  '/reportes': 'reportes.ver',
  '/bi': 'bi.ver',
};

// Decode JWT payload without verification (for client-side expiration check)
const decodeTokenPayload = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};

// Check if a JWT token is expired client-side
const isTokenExpired = (token) => {
  if (!token) return true;
  const payload = decodeTokenPayload(token);
  if (!payload || !payload.exp) return true;
  // Token expired if exp is in the past (with 30s buffer)
  return (payload.exp * 1000) < (Date.now() - 30000);
};

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [empresa, setEmpresa] = useState(null);
  const [userPermisos, setUserPermisos] = useState([]);
  const [token, setToken] = useState(() => {
    const stored = localStorage.getItem('token');
    // Immediately discard expired tokens on init
    if (stored && isTokenExpired(stored)) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('userPermisos');
      return null;
    }
    return stored;
  });
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  const [primaryColor, setPrimaryColor] = useState(localStorage.getItem('primaryColor') || 'blue');
  const [loading, setLoading] = useState(true);

  // Apply theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Apply primary color
  useEffect(() => {
    document.documentElement.setAttribute('data-theme-color', primaryColor);
    localStorage.setItem('primaryColor', primaryColor);
  }, [primaryColor]);

  // Fetch user permissions when user changes
  const fetchUserPermisos = async (userId, authToken) => {
    try {
      const res = await fetch(`${API_URL}/usuarios/${userId}/permisos`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const permisos = await res.json();
        setUserPermisos(permisos.map(p => p.clave));
        localStorage.setItem('userPermisos', JSON.stringify(permisos.map(p => p.clave)));
      } else if (res.status === 401) {
        // Token rejected by backend
        logout();
      }
    } catch (e) {
      console.error('Failed to fetch user permissions:', e);
    }
  };

  // Check auth on mount - validate token against backend
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        // Client-side expiration check first
        if (isTokenExpired(token)) {
          console.info('Token expirado, cerrando sesión.');
          logout();
          setLoading(false);
          return;
        }

        try {
          // Validate token against backend /auth/me
          const meRes = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });

          if (!meRes.ok) {
            console.info('Sesión inválida o expirada (backend rechazó el token).');
            logout();
            setLoading(false);
            return;
          }

          const userData = await meRes.json();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));

          // Load cached permissions temporarily, then refresh
          const cachedPermisos = JSON.parse(localStorage.getItem('userPermisos') || '[]');
          setUserPermisos(cachedPermisos);

          // Fetch empresa
          const empresaRes = await fetch(`${API_URL}/empresas/${userData.empresa_id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (empresaRes.ok) {
            const empresaData = await empresaRes.json();
            setEmpresa(empresaData);
          }

          // Refresh permissions from backend
          await fetchUserPermisos(userData.id, token);
        } catch (e) {
          console.error('Auth check failed:', e);
          logout();
        }
      }
      setLoading(false);
    };
    checkAuth();
  }, [token]);

  // Periodic token expiration check (every 60 seconds)
  useEffect(() => {
    if (!token) return;

    const interval = setInterval(() => {
      if (isTokenExpired(token)) {
        console.info('Sesión expirada. Requiere nuevo inicio de sesión.');
        logout();
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [token]);

  const login = async (email, password) => {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Error de autenticación');
    }
    
    const data = await res.json();
    setToken(data.access_token);
    setUser(data.usuario);
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.usuario));
    
    // Fetch empresa
    const empresaRes = await fetch(`${API_URL}/empresas/${data.usuario.empresa_id}`, {
      headers: { 'Authorization': `Bearer ${data.access_token}` }
    });
    if (empresaRes.ok) {
      const empresaData = await empresaRes.json();
      setEmpresa(empresaData);
    }
    
    // Fetch user permissions
    await fetchUserPermisos(data.usuario.id, data.access_token);
    
    return data;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setEmpresa(null);
    setUserPermisos([]);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('userPermisos');
  };

  const api = async (endpoint, options = {}) => {
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers
      },
      ...options
    };
    
    try {
      const res = await fetch(`${API_URL}${endpoint}`, config);
      
      if (!res.ok) {
        // Try to extract detailed error message
        let errorMessage = 'Error en la solicitud';
        try {
          const error = await res.json();
          errorMessage = error.detail || error.message || errorMessage;
        } catch (e) {
          // If response is not JSON, use status-based messages
          if (res.status === 400) {
            errorMessage = 'Datos inv\u00e1lidos en la solicitud';
          } else if (res.status === 401) {
            errorMessage = 'Sesi\u00f3n expirada. Por favor inicie sesi\u00f3n nuevamente';
            logout();
          } else if (res.status === 403) {
            errorMessage = 'No tiene permisos para realizar esta acci\u00f3n';
          } else if (res.status === 404) {
            errorMessage = 'Recurso no encontrado';
          } else if (res.status === 409) {
            errorMessage = 'Conflicto: el recurso ya existe o tiene dependencias';
          } else if (res.status === 422) {
            errorMessage = 'Error de validaci\u00f3n de datos';
          } else if (res.status >= 500) {
            errorMessage = 'Error del servidor. Contacte al administrador.';
          } else {
            errorMessage = `Error ${res.status}: ${res.statusText}`;
          }
        }
        throw new Error(errorMessage);
      }
      
      return await res.json();
    } catch (error) {
      // Network errors or fetch failures
      if (error.name === 'TypeError' || error.message.includes('Failed to fetch')) {
        throw new Error('Error de conexi\u00f3n. Verifique su internet e int\u00e9ntelo nuevamente.');
      }
      // Re-throw our custom errors
      throw error;
    }
  };

  // Check if user has a specific permission
  const hasPermission = (permiso) => {
    if (!permiso) return true; // null permission means everyone can access
    if (!user) return false;
    // Admin role has all permissions
    if (user.rol?.nombre === 'ADMIN' || user.rol_id === 1) return true;
    return userPermisos.includes(permiso);
  };

  // Check if user can access a route
  const canAccessRoute = (path) => {
    const requiredPermission = ROUTE_PERMISSIONS[path];
    return hasPermission(requiredPermission);
  };

  const value = {
    user,
    empresa,
    token,
    theme,
    primaryColor,
    loading,
    userPermisos,
    login,
    logout,
    setTheme,
    setPrimaryColor,
    api,
    API_URL,
    hasPermission,
    canAccessRoute,
    ROUTE_PERMISSIONS
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

export default AppContext;
