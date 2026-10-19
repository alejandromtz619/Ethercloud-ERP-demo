import { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';

// Ciudad y corrimiento de la factura en papel (Sistema › Configuración › Documentos impresos). Se piden
// una vez por sesión y los comparten todas las impresiones.
const PREDETERMINADOS = { ciudad_factura: '', ajuste_x_mm: 0, ajuste_y_mm: 0 };
let pedido = null;

export function useAjustesImpresion() {
  const { api, token } = useApp();
  const [ajustes, setAjustes] = useState(PREDETERMINADOS);
  useEffect(() => {
    if (!token) return undefined;
    let vigente = true;
    pedido = pedido || api('/configuracion/impresion').catch(() => { pedido = null; return PREDETERMINADOS; });
    pedido.then((a) => vigente && setAjustes({ ...PREDETERMINADOS, ...a }));
    return () => { vigente = false; };
  }, [api, token]);
  return ajustes;
}

// Después de cambiar la configuración: la próxima impresión vuelve a pedirla
export const olvidarAjustesImpresion = () => { pedido = null; };
