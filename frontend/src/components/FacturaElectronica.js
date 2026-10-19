import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { CheckCircle2, FileText, Loader2, Printer, RefreshCw, XCircle } from 'lucide-react';
import { toast } from 'sonner';

// Factura electrónica de una venta (ventaId) o de una factura agrupada (grupalId): estado en SIFEN,
// emitir, reintentar e imprimir el KuDE (ticket de 80 mm o A4). Backend: /api/fiscal (backend/fiscal).

export const ESTADOS_FE = {
  POR_ENVIAR: { texto: 'Por enviar', clase: 'bg-amber-100 text-amber-900', camino: true },
  GENERADO: { texto: 'Enviando a SIFEN', clase: 'bg-blue-100 text-blue-900', camino: true },
  ENVIADO: { texto: 'En SIFEN', clase: 'bg-blue-100 text-blue-900', camino: true },
  APROBADO: { texto: 'Aprobada', clase: 'bg-green-100 text-green-900' },
  RECHAZADO: { texto: 'Rechazada', clase: 'bg-red-100 text-red-900', corregir: true },
  INVALIDO: { texto: 'Con errores', clase: 'bg-red-100 text-red-900', corregir: true },
  CANCELADO: { texto: 'Cancelada', clase: 'bg-slate-100 text-slate-700' },
};

export function EstadoFE({ documento }) {
  if (!documento) return null;
  const e = ESTADOS_FE[documento.estado] || { texto: documento.estado, clase: '' };
  return <Badge variant="outline" className={`border-0 ${e.clase}`} data-testid="estado-fe">{e.texto}</Badge>;
}

const SEGUNDOS_CONSULTA = 4;

export default function PanelFacturaElectronica({ ventaId, grupalId, onCambio }) {
  const { api, token, API_URL } = useApp();
  const [documento, setDocumento] = useState(undefined); // undefined = cargando, null = no tiene
  const [trabajando, setTrabajando] = useState(false);
  const [errores, setErrores] = useState([]);
  const [pideCheque, setPideCheque] = useState(false);
  const [cheque, setCheque] = useState({ numero: '', banco: '' });
  const consultas = useRef(0);

  const cargar = useCallback(async () => {
    if (ventaId) {
      const docs = await api(`/fiscal/ventas/${ventaId}/documentos`);
      setDocumento(docs.filter((d) => d.tipo_documento === 1 && d.estado !== 'CANCELADO').pop() || null);
    } else {
      const estados = await api(`/fiscal/facturas-grupales/estados?ids=${grupalId}`);
      setDocumento(estados[String(grupalId)] || null);
    }
  }, [api, ventaId, grupalId]);

  useEffect(() => { cargar().catch((e) => { setDocumento(null); setErrores([e.message]); }); }, [cargar]);

  // Mientras va camino a SIFEN, se consulta solo (hasta ~2 minutos; después, con el botón)
  useEffect(() => {
    if (!documento || !ESTADOS_FE[documento.estado]?.camino || consultas.current > 30) return undefined;
    const t = setTimeout(async () => {
      consultas.current += 1;
      try {
        const d = await api(`/fiscal/documentos/${documento.id}/reintentar`, { method: 'POST' });
        setDocumento(d);
        onCambio?.(d);
      } catch { /* se reintenta en la próxima vuelta */ }
    }, SEGUNDOS_CONSULTA * 1000);
    return () => clearTimeout(t);
  }, [api, documento, onCambio]);

  const emitir = async () => {
    setTrabajando(true);
    setErrores([]);
    try {
      const ruta = ventaId ? `/fiscal/ventas/${ventaId}/factura` : `/fiscal/facturas-grupales/${grupalId}/factura`;
      const cuerpo = pideCheque ? { cheque } : {};
      // api() muestra el detalle como texto; acá se necesita la lista de errores: fetch directo
      const res = await fetch(`${API_URL}${ruta}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(cuerpo),
      });
      const datos = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detalle = datos.detail;
        const lista = Array.isArray(detalle?.errores) ? detalle.errores : [typeof detalle === 'string' ? detalle : detalle?.mensaje || `Error ${res.status}`];
        if (lista.some((t) => t.toLowerCase().includes('cheque'))) setPideCheque(true);
        if (detalle?.documento) setDocumento(detalle.documento);
        setErrores(lista);
        return;
      }
      consultas.current = 0;
      setDocumento(datos);
      onCambio?.(datos);
      toast.success(`Factura electrónica ${datos.numero} emitida`);
    } catch (e) {
      setErrores([e.message]);
    } finally {
      setTrabajando(false);
    }
  };

  const reintentar = async () => {
    setTrabajando(true);
    setErrores([]);
    try {
      consultas.current = 0;
      const d = await api(`/fiscal/documentos/${documento.id}/reintentar`, { method: 'POST' });
      setDocumento(d);
      onCambio?.(d);
    } catch (e) {
      setErrores([e.message]);
    } finally {
      setTrabajando(false);
    }
  };

  // El KuDE lo genera el proveedor: se pide con la sesión y se abre en el visor de PDF para imprimir
  const imprimir = async (formato) => {
    const ventana = window.open('', '_blank');
    try {
      const res = await fetch(`${API_URL}/fiscal/documentos/${documento.id}/kude?formato=${formato}`,
                              { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Error ${res.status}`);
      const url = URL.createObjectURL(await res.blob());
      if (ventana) ventana.location.href = url; else window.open(url, '_blank');
    } catch (e) {
      ventana?.close();
      toast.error(`No se pudo bajar el KuDE: ${e.message}`);
    }
  };

  if (documento === undefined) {
    return <div className="flex justify-center py-4"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>;
  }
  const estado = documento ? ESTADOS_FE[documento.estado] || {} : {};

  return (
    <div className="space-y-3 rounded-lg border p-3 text-sm" data-testid="panel-fe">
      {documento ? (
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <FileText className="h-4 w-4" />
            <span className="font-medium" data-testid="numero-fe">{documento.numero}</span>
            <EstadoFE documento={documento} />
            {estado.camino && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
            {documento.ambiente !== 'PRODUCCION' && <Badge variant="secondary">{documento.ambiente}</Badge>}
          </div>
          {documento.cdc && <p className="font-mono text-[11px] text-muted-foreground break-all">CDC {documento.cdc}</p>}
          {documento.mensaje && (
            <p className={estado.corregir ? 'text-destructive' : 'text-muted-foreground'}>{documento.mensaje}</p>
          )}
          {estado.corregir && (
            <p className="text-xs text-muted-foreground">Corregí los datos (por ejemplo el RUC del cliente) y reintentá: se usa el mismo número.</p>
          )}
        </div>
      ) : (
        <p className="text-muted-foreground">Todavía no tiene factura electrónica.</p>
      )}

      {pideCheque && !documento && (
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1"><Label htmlFor="fe-cheque-numero">N° de cheque</Label>
            <Input id="fe-cheque-numero" value={cheque.numero} onChange={(e) => setCheque({ ...cheque, numero: e.target.value })} /></div>
          <div className="space-y-1"><Label htmlFor="fe-cheque-banco">Banco</Label>
            <Input id="fe-cheque-banco" value={cheque.banco} onChange={(e) => setCheque({ ...cheque, banco: e.target.value })} /></div>
        </div>
      )}

      {errores.length > 0 && (
        <ul className="space-y-1 rounded-md bg-destructive/5 p-2 text-destructive" data-testid="errores-fe">
          {errores.map((t, i) => <li key={i} className="flex gap-1.5"><XCircle className="h-4 w-4 shrink-0 mt-0.5" />{t}</li>)}
        </ul>
      )}

      <div className="flex flex-wrap gap-2">
        {!documento && (
          <Button size="sm" onClick={emitir} disabled={trabajando} data-testid="emitir-fe">
            {trabajando ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <CheckCircle2 className="h-4 w-4 mr-1" />}
            Emitir factura electrónica
          </Button>
        )}
        {documento?.cdc && (
          <>
            <Button size="sm" variant="outline" onClick={() => imprimir('ticket')} data-testid="kude-ticket">
              <Printer className="h-4 w-4 mr-1" />Ticket
            </Button>
            <Button size="sm" variant="outline" onClick={() => imprimir('a4')} data-testid="kude-a4">
              <Printer className="h-4 w-4 mr-1" />A4
            </Button>
          </>
        )}
        {documento && (estado.camino || estado.corregir) && (
          <Button size="sm" variant="ghost" onClick={reintentar} disabled={trabajando} data-testid="reintentar-fe">
            <RefreshCw className="h-4 w-4 mr-1" />{estado.corregir ? 'Reintentar' : 'Consultar ahora'}
          </Button>
        )}
      </div>
    </div>
  );
}
