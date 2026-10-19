import { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';

// Módulos contratados de la instancia (GET /api/sistema/modulos: fe, crm...). Se piden una vez por sesión.
let pedido = null;

export function useModulos() {
  const { api, token } = useApp();
  const [modulos, setModulos] = useState({});
  useEffect(() => {
    if (!token) return undefined;
    let vigente = true;
    pedido = pedido || api('/sistema/modulos').catch(() => { pedido = null; return {}; });
    pedido.then((m) => vigente && setModulos(m || {}));
    return () => { vigente = false; };
  }, [api, token]);
  return modulos;
}
