import React, { useCallback, useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ESTADOS_FE, EstadoFE } from '../components/FacturaElectronica';
import { Ban, ChevronLeft, ChevronRight, FileCode, Loader2, Printer, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';

// Todos los documentos electrónicos (facturas y notas de crédito) con su estado en SIFEN, los eventos
// (cancelaciones e inutilizaciones) e inutilizar números salteados. Backend: /api/fiscal.

const POR_PAGINA = 50;
const GRUPOS = [
  { clave: '', texto: 'Todos', estados: null },
  { clave: 'APROBADO', texto: 'Aprobados', estados: ['APROBADO'] },
  { clave: 'POR_ENVIAR,GENERADO,ENVIADO', texto: 'En camino', estados: ['POR_ENVIAR', 'GENERADO', 'ENVIADO'] },
  { clave: 'RECHAZADO,INVALIDO', texto: 'Con problemas', estados: ['RECHAZADO', 'INVALIDO'] },
  { clave: 'CANCELADO,INUTILIZADO', texto: 'Cancelados e inutilizados', estados: ['CANCELADO', 'INUTILIZADO'] },
];
const TIPOS = { 1: 'Factura', 4: 'Autofactura', 5: 'Nota de crédito', 6: 'Nota de débito', 7: 'Nota de remisión' };
const EVENTOS = { cancelacion: 'Cancelación', inutilizacion: 'Inutilización' };
const fecha = (iso) => (iso ? new Date(iso).toLocaleString('es-PY', { dateStyle: 'short', timeStyle: 'short' }) : '—');
const gs = (n) => `Gs. ${Math.round(Number(n || 0)).toLocaleString('es-PY')}`;

function Documentos({ alCambiar }) {
  const { api, token, API_URL } = useApp();
  const [filtros, setFiltros] = useState({ estado: '', tipo_documento: '', q: '', desde: '', hasta: '' });
  const [pagina, setPagina] = useState(0);
  const [datos, setDatos] = useState(null);
  const [trabajando, setTrabajando] = useState(null);

  const cargar = useCallback(() => {
    const params = new URLSearchParams({ limit: POR_PAGINA, offset: pagina * POR_PAGINA });
    Object.entries(filtros).forEach(([k, v]) => v && params.set(k, v.trim ? v.trim() : v));
    return api(`/fiscal/documentos?${params}`).then(setDatos).catch((e) => toast.error(e.message));
  }, [api, filtros, pagina]);

  useEffect(() => {
    const t = setTimeout(cargar, filtros.q ? 350 : 0);
    return () => clearTimeout(t);
  }, [cargar, filtros.q]);

  const filtrar = (cambio) => { setPagina(0); setFiltros((f) => ({ ...f, ...cambio })); };
  const cuenta = (grupo) => (datos?.por_estado ? (grupo.estados ?? Object.keys(datos.por_estado))
    .reduce((s, e) => s + (datos.por_estado[e] || 0), 0) : null);

  const bajar = async (doc, que) => {
    const ventana = que === 'xml' ? null : window.open('', '_blank');
    try {
      const ruta = que === 'xml' ? 'xml' : `kude?formato=${que}`;
      const res = await fetch(`${API_URL}/fiscal/documentos/${doc.id}/${ruta}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Error ${res.status}`);
      const url = URL.createObjectURL(await res.blob());
      if (que === 'xml') {
        const a = document.createElement('a');
        a.href = url;
        a.download = `${doc.cdc || doc.numero}.xml`;
        a.click();
      } else if (ventana) {
        ventana.location.href = url;
      } else {
        window.open(url, '_blank');
      }
    } catch (e) {
      ventana?.close();
      toast.error(`No se pudo bajar el ${que === 'xml' ? 'XML' : 'KuDE'}: ${e.message}`);
    }
  };

  const reintentar = async (doc) => {
    setTrabajando(doc.id);
    try {
      const nuevo = await api(`/fiscal/documentos/${doc.id}/reintentar`, { method: 'POST' });
      toast.success(`${nuevo.numero}: ${ESTADOS_FE[nuevo.estado]?.texto || nuevo.estado}`);
      cargar();
      alCambiar();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setTrabajando(null);
    }
  };

  const paginas = datos ? Math.max(1, Math.ceil(datos.total / POR_PAGINA)) : 1;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Estado">
        {GRUPOS.map((g) => (
          <Button key={g.clave} size="sm" variant={filtros.estado === g.clave ? 'default' : 'outline'}
                  onClick={() => filtrar({ estado: g.clave })} data-testid={`grupo-${g.texto}`}>
            {g.texto}{cuenta(g) !== null && <span className="ml-1.5 opacity-70">{cuenta(g)}</span>}
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input value={filtros.q} onChange={(e) => filtrar({ q: e.target.value })} placeholder="Número, CDC o venta"
                 className="pl-8 w-64" data-testid="buscar-documento" />
        </div>
        <select value={filtros.tipo_documento} onChange={(e) => filtrar({ tipo_documento: e.target.value })}
                className="h-9 rounded-md border border-input bg-transparent px-2 text-sm" aria-label="Tipo de documento">
          <option value="">Todos los tipos</option>
          <option value="1">Facturas</option>
          <option value="5">Notas de crédito</option>
        </select>
        <div className="flex items-center gap-2 text-sm">
          <Label htmlFor="docs-desde">Desde</Label>
          <Input id="docs-desde" type="date" value={filtros.desde} onChange={(e) => filtrar({ desde: e.target.value })} className="w-40" />
          <Label htmlFor="docs-hasta">Hasta</Label>
          <Input id="docs-hasta" type="date" value={filtros.hasta} onChange={(e) => filtrar({ hasta: e.target.value })} className="w-40" />
        </div>
      </div>

      {!datos ? <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /> : datos.items.length === 0 ? (
        <p className="text-sm text-muted-foreground py-6">No hay documentos con esos filtros.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm" data-testid="tabla-documentos">
            <thead className="bg-muted/50 text-left">
              <tr>
                <th className="px-3 py-2 font-medium">Fecha</th>
                <th className="px-3 py-2 font-medium">Documento</th>
                <th className="px-3 py-2 font-medium">Origen</th>
                <th className="px-3 py-2 font-medium text-right">Total</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {datos.items.map((d) => {
                const e = ESTADOS_FE[d.estado] || {};
                return (
                  <tr key={d.id} className="border-t align-top" data-testid={`documento-${d.id}`}>
                    <td className="px-3 py-2 whitespace-nowrap">{fecha(d.creado_en)}</td>
                    <td className="px-3 py-2">
                      <p className="font-medium">{TIPOS[d.tipo_documento] || d.tipo} {d.numero}</p>
                      {d.cdc && <p className="font-mono text-[11px] text-muted-foreground break-all">{d.cdc}</p>}
                      {e.corregir && d.mensaje && <p className="text-xs text-destructive mt-1 max-w-md">{d.mensaje}</p>}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">
                      {d.venta_id ? `Venta #${d.venta_id}` : d.factura_grupal_id ? `Factura agrupada #${d.factura_grupal_id}` : '—'}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">{gs(d.total)}</td>
                    <td className="px-3 py-2">
                      <EstadoFE documento={d} />
                      {d.ambiente !== 'PRODUCCION' && <Badge variant="outline" className="ml-1 text-[10px]">{d.ambiente}</Badge>}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-1">
                        {d.cdc && !['INUTILIZADO', 'INVALIDO'].includes(d.estado) && (
                          <>
                            <Button size="sm" variant="ghost" onClick={() => bajar(d, 'a4')} title="KuDE A4"><Printer className="h-4 w-4" /></Button>
                            <Button size="sm" variant="ghost" onClick={() => bajar(d, 'xml')} title="XML"><FileCode className="h-4 w-4" /></Button>
                          </>
                        )}
                        {(e.corregir || e.camino) && (
                          <Button size="sm" variant="ghost" disabled={trabajando === d.id} onClick={() => reintentar(d)}
                                  title={e.corregir ? 'Reemitir con los datos actuales' : 'Consultar en SIFEN'} data-testid={`reintentar-${d.id}`}>
                            <RefreshCw className={`h-4 w-4 ${trabajando === d.id ? 'animate-spin' : ''}`} />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {datos && datos.total > POR_PAGINA && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button size="sm" variant="outline" disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}><ChevronLeft className="h-4 w-4" /></Button>
          <span>Página {pagina + 1} de {paginas}</span>
          <Button size="sm" variant="outline" disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}><ChevronRight className="h-4 w-4" /></Button>
        </div>
      )}
    </div>
  );
}

function Eventos({ version }) {
  const { api } = useApp();
  const [eventos, setEventos] = useState(null);
  useEffect(() => { api('/fiscal/eventos?limit=200').then(setEventos).catch((e) => toast.error(e.message)); }, [api, version]);
  if (!eventos) return <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />;
  if (eventos.length === 0) return <p className="text-sm text-muted-foreground py-6">Todavía no hubo cancelaciones ni inutilizaciones.</p>;
  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="w-full text-sm" data-testid="tabla-eventos">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="px-3 py-2 font-medium">Fecha</th>
            <th className="px-3 py-2 font-medium">Evento</th>
            <th className="px-3 py-2 font-medium">Números</th>
            <th className="px-3 py-2 font-medium">Motivo</th>
            <th className="px-3 py-2 font-medium">Resultado</th>
          </tr>
        </thead>
        <tbody>
          {eventos.map((e) => (
            <tr key={e.id} className="border-t align-top">
              <td className="px-3 py-2 whitespace-nowrap">{fecha(e.creado_en)}</td>
              <td className="px-3 py-2">{EVENTOS[e.tipo] || e.tipo} · {TIPOS[e.tipo_documento] || ''}</td>
              <td className="px-3 py-2 whitespace-nowrap">{e.numeros}</td>
              <td className="px-3 py-2">{e.motivo}</td>
              <td className="px-3 py-2">
                <Badge variant="outline" className={`border-0 ${e.estado === 'APROBADO' ? 'bg-green-100 text-green-900' : 'bg-red-100 text-red-900'}`}>
                  {e.estado === 'APROBADO' ? 'Aprobado' : e.estado}
                </Badge>
                {e.mensaje && <p className="text-xs text-muted-foreground mt-1">{e.mensaje}</p>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Inutilizar({ alListo }) {
  const { api } = useApp();
  const [datos, setDatos] = useState({ tipo_documento: '1', desde: '', hasta: '', motivo: '' });
  const [enviando, setEnviando] = useState(false);
  const desde = Number(datos.desde);
  const hasta = Number(datos.hasta || datos.desde);
  const valido = desde > 0 && hasta >= desde && hasta - desde < 1000 && datos.motivo.trim().length >= 5;

  const enviar = async (e) => {
    e.preventDefault();
    const cantidad = hasta - desde + 1;
    if (!window.confirm(`Se ${cantidad === 1 ? 'inutiliza 1 número' : `inutilizan ${cantidad} números`} en SIFEN. No se puede deshacer. ¿Seguir?`)) return;
    setEnviando(true);
    try {
      const r = await api('/fiscal/inutilizaciones', {
        method: 'POST',
        body: JSON.stringify({ tipo_documento: Number(datos.tipo_documento), desde, hasta, motivo: datos.motivo.trim() }),
      });
      toast.success(`Inutilizados: ${r.numeros}`);
      setDatos({ ...datos, desde: '', hasta: '', motivo: '' });
      alListo();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="space-y-4 max-w-xl" data-testid="form-inutilizar">
      <p className="text-sm text-muted-foreground">
        Para números que se saltearon y nunca se van a usar (por ejemplo, un error de numeración). Cada número
        inutilizado queda informado a SIFEN. Los números con un documento emitido no se pueden inutilizar; para una
        factura rechazada, usá “Inutilizar número” desde la venta.
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="space-y-1">
          <Label htmlFor="inut-tipo">Tipo</Label>
          <select id="inut-tipo" value={datos.tipo_documento} onChange={(e) => setDatos({ ...datos, tipo_documento: e.target.value })}
                  className="h-9 w-full rounded-md border border-input bg-transparent px-2 text-sm">
            <option value="1">Factura</option>
            <option value="5">Nota de crédito</option>
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="inut-desde">Desde el número</Label>
          <Input id="inut-desde" type="number" min="1" value={datos.desde} onChange={(e) => setDatos({ ...datos, desde: e.target.value })} />
        </div>
        <div className="space-y-1">
          <Label htmlFor="inut-hasta">Hasta (opcional)</Label>
          <Input id="inut-hasta" type="number" min="1" value={datos.hasta} placeholder={datos.desde}
                 onChange={(e) => setDatos({ ...datos, hasta: e.target.value })} />
        </div>
      </div>
      <div className="space-y-1">
        <Label htmlFor="inut-motivo">Motivo</Label>
        <Input id="inut-motivo" value={datos.motivo} maxLength={500} onChange={(e) => setDatos({ ...datos, motivo: e.target.value })}
               placeholder="Ej.: salto de numeración por error del sistema" />
      </div>
      {hasta - desde >= 1000 && <p className="text-sm text-destructive">Hasta 1000 números por vez.</p>}
      <Button type="submit" disabled={!valido || enviando} data-testid="inutilizar-rango">
        {enviando ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Ban className="h-4 w-4 mr-1" />}Inutilizar
      </Button>
    </form>
  );
}

export default function DocumentosElectronicos() {
  const { api, hasPermission } = useApp();
  const [estado, setEstado] = useState(null);
  const [version, setVersion] = useState(0);
  const cambiar = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => { api('/fiscal/estado').then(setEstado).catch(() => setEstado({ conectado: false })); }, [api, version]);

  return (
    <div className="space-y-6" data-testid="documentos-electronicos">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold" style={{ fontFamily: 'Manrope' }}>Documentos electrónicos</h1>
        {estado?.conectado && <Badge variant="outline">{estado.ambiente}</Badge>}
        {estado && !estado.conectado && <Badge variant="destructive">SIFEN SIS sin conexión{estado.error ? `: ${estado.error}` : ''}</Badge>}
      </div>
      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-base">Facturas y notas de crédito en SIFEN</CardTitle></CardHeader>
        <CardContent>
          <Tabs defaultValue="documentos">
            <TabsList>
              <TabsTrigger value="documentos">Documentos</TabsTrigger>
              <TabsTrigger value="eventos" data-testid="pestana-eventos">Eventos</TabsTrigger>
              {hasPermission('sistema.integraciones') && <TabsTrigger value="inutilizar" data-testid="pestana-inutilizar">Inutilizar números</TabsTrigger>}
            </TabsList>
            <TabsContent value="documentos" className="pt-4"><Documentos alCambiar={cambiar} /></TabsContent>
            <TabsContent value="eventos" className="pt-4"><Eventos version={version} /></TabsContent>
            {hasPermission('sistema.integraciones') && (
              <TabsContent value="inutilizar" className="pt-4"><Inutilizar alListo={cambiar} /></TabsContent>
            )}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
