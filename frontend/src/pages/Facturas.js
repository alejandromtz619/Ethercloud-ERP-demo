import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Checkbox } from '../components/ui/checkbox';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../components/ui/dialog';
import { FileText, Loader2, Printer, Users, ChevronRight, CheckSquare, Square, Search, CreditCard, Banknote } from 'lucide-react';
import { toast } from 'sonner';
import { FacturaPrint } from '../components/PrintModal';
import PanelFacturaElectronica, { EstadoFE } from '../components/FacturaElectronica';
import { useModulos } from '../lib/modulos';
import { useAjustesImpresion } from '../lib/ajustesImpresion';

const PRINT_CSS = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { margin: 0; padding: 0; background: white; }
  .factura-print { margin: 0; padding: 0; page-break-after: always; }
  @media print {
    @page { size: auto; margin: 15mm 8mm 10mm 8mm; }
    body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .factura-print { width: 240mm !important; height: 200mm !important; margin: 0 !important; padding: 0 !important; }
  }
`;

const CLIENTES_VISIBLES = 100;

const Facturas = () => {
  const { api, empresa } = useApp();

  // ── State ──────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('facturar');
  const [clientesPendientes, setClientesPendientes] = useState([]);
  const [clienteSeleccionado, setClienteSeleccionado] = useState(null);
  const [boletasPendientes, setBoletasPendientes] = useState([]);
  const [boletasSeleccionadas, setBoletasSeleccionadas] = useState(new Set());
  const [facturasEmitidas, setFacturasEmitidas] = useState([]);
  const [loadingClientes, setLoadingClientes] = useState(false);
  const [loadingBoletas, setLoadingBoletas] = useState(false);
  const [loadingEmitidas, setLoadingEmitidas] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [facturaImpresionData, setFacturaImpresionData] = useState(null);
  const [filtroCliente, setFiltroCliente] = useState('');
  // Se dibujan de a 100: con miles de clientes pendientes la lista trababa la pantalla
  const [clientesVisibles, setClientesVisibles] = useState(CLIENTES_VISIBLES);
  const [modalTipoPago, setModalTipoPago] = useState(false);
  const [limitarBoletas, setLimitarBoletas] = useState(true);
  const LIMITE_BOLETAS = 50;
  const facturaRef = useRef(null);

  // ── Helpers ────────────────────────────────────────────────────────────────
  const fmt = (v) =>
    new Intl.NumberFormat('es-PY', { style: 'currency', currency: 'PYG', minimumFractionDigits: 0 }).format(v);

  const fmtDate = (iso) =>
    iso ? new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('es-PY', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'America/Asuncion' }) : '-';

  // ── Cargar clientes pendientes ─────────────────────────────────────────────
  const fetchClientesPendientes = useCallback(async () => {
    if (!empresa?.id) return;
    setLoadingClientes(true);
    try {
      const data = await api(`/facturas/clientes-pendientes?empresa_id=${empresa.id}`);
      setClientesPendientes(data);
    } catch (e) {
      toast.error('Error al cargar clientes pendientes');
    } finally {
      setLoadingClientes(false);
    }
  }, [api, empresa?.id]);

  // ── Cargar facturas emitidas ───────────────────────────────────────────────
  const fetchFacturasEmitidas = useCallback(async () => {
    if (!empresa?.id) return;
    setLoadingEmitidas(true);
    try {
      const data = await api(`/facturas/grupales?empresa_id=${empresa.id}`);
      setFacturasEmitidas(data);
    } catch (e) {
      toast.error('Error al cargar facturas emitidas');
    } finally {
      setLoadingEmitidas(false);
    }
  }, [api, empresa?.id]);

  useEffect(() => {
    fetchClientesPendientes();
    fetchFacturasEmitidas();
  }, [fetchClientesPendientes, fetchFacturasEmitidas]);

  // Factura electrónica de las agrupadas (sólo con el módulo fe)
  const modulos = useModulos();
  const ajustesImpresion = useAjustesImpresion();
  const electronicaPorDefecto = !!modulos.fe && ajustesImpresion.factura_modo === 'electronica';
  const [facturasFE, setFacturasFE] = useState({});
  const [grupalFE, setGrupalFE] = useState(null); // agrupada abierta en el panel de factura electrónica
  const cargarEstadosFE = useCallback(() => {
    const ids = facturasEmitidas.slice(0, 200).map((f) => f.id).join(',');
    if (modulos.fe && ids) api(`/fiscal/facturas-grupales/estados?ids=${ids}`).then(setFacturasFE).catch(() => {});
  }, [api, modulos.fe, facturasEmitidas]);
  useEffect(() => { cargarEstadosFE(); }, [cargarEstadosFE]);

  // ── Trigger print when data is ready ──────────────────────────────────────
  useEffect(() => {
    if (!facturaImpresionData) return;
    const timer = setTimeout(() => {
      if (facturaRef.current) {
        const html = facturaRef.current.innerHTML;
        const win = window.open('', '_blank');
        if (win) {
          win.document.write(
            `<html><head><title>Factura ${facturaImpresionData.numero}</title><meta charset="UTF-8"><style>${PRINT_CSS}</style></head><body>${html}</body></html>`
          );
          win.document.close();
          win.print();
          win.close();
        }
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [facturaImpresionData]);

  // ── Seleccionar cliente ────────────────────────────────────────────────────
  const handleSeleccionarCliente = async (cliente) => {
    setClienteSeleccionado(cliente);
    setBoletasSeleccionadas(new Set());
    setLoadingBoletas(true);
    try {
      const data = await api(
        `/facturas/boletas-pendientes/${cliente.cliente_id}?empresa_id=${empresa.id}`
      );
      setBoletasPendientes(data);
      const ids = data.map((b) => b.id);
      if (limitarBoletas && ids.length > LIMITE_BOLETAS) {
        setBoletasSeleccionadas(new Set(ids.slice(0, LIMITE_BOLETAS)));
        toast.info(`Se seleccionaron las primeras ${LIMITE_BOLETAS} boletas (límite activo)`);
      } else {
        setBoletasSeleccionadas(new Set(ids));
      }
    } catch (e) {
      toast.error('Error al cargar boletas del cliente');
    } finally {
      setLoadingBoletas(false);
    }
  };

  const toggleBoleta = (id) => {
    setBoletasSeleccionadas((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (limitarBoletas && next.size >= LIMITE_BOLETAS) {
          toast.warning(`Límite de ${LIMITE_BOLETAS} boletas activo. Desactívelo para seleccionar más.`);
          return prev;
        }
        next.add(id);
      }
      return next;
    });
  };

  const toggleTodas = () => {
    if (boletasSeleccionadas.size === boletasPendientes.length) {
      setBoletasSeleccionadas(new Set());
    } else {
      const ids = boletasPendientes.map((b) => b.id);
      if (limitarBoletas && ids.length > LIMITE_BOLETAS) {
        setBoletasSeleccionadas(new Set(ids.slice(0, LIMITE_BOLETAS)));
        toast.info(`Se seleccionaron las primeras ${LIMITE_BOLETAS} boletas (límite activo)`);
      } else {
        setBoletasSeleccionadas(new Set(ids));
      }
    }
  };

  // ── Generar factura grupal ─────────────────────────────────────────────────
  const handleGenerarFactura = () => {
    if (!clienteSeleccionado) return;
    if (boletasSeleccionadas.size === 0) {
      toast.error('Seleccione al menos una boleta');
      return;
    }
    setModalTipoPago(true);
  };

  const confirmarGenerarFactura = async (cobrarCredito) => {
    setModalTipoPago(false);

    // Validate: if credit mode, all selected boletas must be CREDITO
    if (!cobrarCredito) {
      const seleccionadas = boletasPendientes.filter((b) => boletasSeleccionadas.has(b.id));
      const hayNoCredito = seleccionadas.some((b) => b.tipo_pago !== 'CREDITO');
      if (hayNoCredito) {
        toast.error('Para factura a crédito, todas las boletas seleccionadas deben ser de tipo CRÉDITO. Facture las boletas de contado por separado.');
        return;
      }
    }

    setSubmitting(true);
    try {
      const result = await api('/facturas/grupal', {
        method: 'POST',
        body: JSON.stringify({
          empresa_id: empresa.id,
          cliente_id: clienteSeleccionado.cliente_id,
          venta_ids: Array.from(boletasSeleccionadas),
          cobrar_credito: cobrarCredito
        })
      });

      toast.success(`Factura ${result.numero} generada${cobrarCredito ? ' (créditos cobrados)' : ' (sin cobrar crédito)'}`);

      const printData = await api(`/facturas/grupal/${result.id}/imprimir`);
      setFacturaImpresionData(printData);

      await fetchClientesPendientes();
      await fetchFacturasEmitidas();

      setClienteSeleccionado(null);
      setBoletasPendientes([]);
      setBoletasSeleccionadas(new Set());
    } catch (e) {
      toast.error(e.message || 'Error al generar factura');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Re-imprimir factura existente ─────────────────────────────────────────
  const handleReimprimir = async (facturaId, numero) => {
    try {
      const data = await api(`/facturas/grupal/${facturaId}/imprimir`);
      setFacturaImpresionData(data);
      toast.info(`Imprimiendo factura ${numero}`);
    } catch (e) {
      toast.error('Error al obtener datos de impresión');
    }
  };

  const totalSeleccionado = boletasPendientes
    .filter((b) => boletasSeleccionadas.has(b.id))
    .reduce((acc, b) => acc + b.total, 0);

  const boletasSeleccionadasArr = boletasPendientes.filter((b) => boletasSeleccionadas.has(b.id));
  const todasCredito = boletasSeleccionadasArr.length > 0 && boletasSeleccionadasArr.every((b) => b.tipo_pago === 'CREDITO');
  const hayMixto = boletasSeleccionadasArr.some((b) => b.tipo_pago !== 'CREDITO') && boletasSeleccionadasArr.some((b) => b.tipo_pago === 'CREDITO');

  // ── Render ─────────────────────────────────────────────────────────────────
  const textoFiltro = filtroCliente.trim().toLowerCase();
  const clientesFiltrados = textoFiltro
    ? clientesPendientes.filter(c =>
        c.nombre?.toLowerCase().includes(textoFiltro) || c.ruc?.toLowerCase().includes(textoFiltro))
    : clientesPendientes;

  useEffect(() => {
    setClientesVisibles(CLIENTES_VISIBLES);
  }, [filtroCliente]);

  return (
    <div className="space-y-6" data-testid="facturas-page">
      <div>
        <h1 className="text-2xl font-bold">Facturas</h1>
        <p className="text-muted-foreground">Facturación agrupada de boletas por cliente</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="facturar">Facturar Boletas</TabsTrigger>
          <TabsTrigger value="emitidas">Facturas Emitidas</TabsTrigger>
        </TabsList>

        {/* ═══════════════ TAB: FACTURAR BOLETAS ═══════════════ */}
        <TabsContent value="facturar" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

            {/* Panel izquierdo: clientes con boletas pendientes */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Users className="h-4 w-4" />
                  Clientes con boletas pendientes
                </CardTitle>
                <div className="relative mt-2">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Buscar por nombre o RUC..."
                    value={filtroCliente}
                    onChange={(e) => setFiltroCliente(e.target.value)}
                    className="pl-8 h-8 text-sm"
                  />
                </div>
              </CardHeader>
              <CardContent className="p-0">
                {loadingClientes ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : clientesPendientes.length === 0 ? (
                  <div className="text-center py-10 px-4">
                    <FileText className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                    <p className="text-muted-foreground text-sm">No hay boletas pendientes de facturar</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {clientesFiltrados
                      .slice(0, clientesVisibles)
                      .map((c) => (
                      <button
                        key={c.cliente_id}
                        onClick={() => handleSeleccionarCliente(c)}
                        className={`w-full text-left px-4 py-3 hover:bg-accent transition-colors flex items-center justify-between group ${
                          clienteSeleccionado?.cliente_id === c.cliente_id
                            ? 'bg-primary/10 border-l-4 border-primary'
                            : ''
                        }`}
                      >
                        <div>
                          <p className="font-medium text-sm">{c.nombre}</p>
                          <p className="text-xs text-muted-foreground">
                            RUC: {c.ruc || <span className="text-destructive font-medium">Sin RUC</span>}
                            {' · '}
                            <Badge variant="secondary" className="text-xs px-1 py-0">
                              {c.boletas_count} boleta{c.boletas_count !== 1 ? 's' : ''}
                            </Badge>
                          </p>
                          <p className="text-xs font-mono-data text-primary mt-0.5">{fmt(c.total_pendiente)}</p>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground shrink-0" />
                      </button>
                    ))}
                    {clientesFiltrados.length > clientesVisibles && (
                      <div className="flex items-center justify-between gap-2 px-4 py-3 text-xs text-muted-foreground">
                        <span>Mostrando {clientesVisibles} de {clientesFiltrados.length.toLocaleString('es-PY')}</span>
                        <Button size="sm" variant="outline" onClick={() => setClientesVisibles(v => v + CLIENTES_VISIBLES)}>
                          Mostrar más
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Panel derecho: boletas del cliente seleccionado */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between text-base">
                  <span className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    {clienteSeleccionado ? `Boletas de ${clienteSeleccionado.nombre}` : 'Seleccione un cliente'}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setLimitarBoletas((v) => !v)}
                      title={limitarBoletas ? 'Límite de 50 boletas activo. Clic para desactivar.' : 'Límite desactivado. Clic para activar.'}
                      className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium border transition-colors ${
                        limitarBoletas
                          ? 'bg-amber-50 border-amber-300 text-amber-700 hover:bg-amber-100'
                          : 'bg-muted border-muted-foreground/30 text-muted-foreground hover:bg-accent'
                      }`}
                    >
                      {limitarBoletas ? '⚠ Límite: 50' : 'Sin límite'}
                    </button>
                    {boletasPendientes.length > 0 && (
                      <Button variant="ghost" size="sm" onClick={toggleTodas} className="h-7 text-xs">
                        {boletasSeleccionadas.size === boletasPendientes.length ? (
                          <><CheckSquare className="h-3 w-3 mr-1" />Deseleccionar todas</>
                        ) : (
                          <><Square className="h-3 w-3 mr-1" />Seleccionar todas</>
                        )}
                      </Button>
                    )}
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {!clienteSeleccionado ? (
                  <div className="text-center py-10">
                    <p className="text-muted-foreground text-sm">Haga clic en un cliente para ver sus boletas</p>
                  </div>
                ) : loadingBoletas ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                  </div>
                ) : boletasPendientes.length === 0 ? (
                  <div className="text-center py-8">
                    <p className="text-muted-foreground text-sm">Sin boletas pendientes</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="divide-y rounded-md border">
                      {boletasPendientes.map((b) => (
                        <div
                          key={b.id}
                          className="flex items-center gap-3 px-3 py-2.5 hover:bg-accent/50 cursor-pointer"
                          onClick={() => toggleBoleta(b.id)}
                        >
                          <Checkbox
                            checked={boletasSeleccionadas.has(b.id)}
                            onCheckedChange={() => toggleBoleta(b.id)}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <div className="flex-1">
                            <p className="text-sm font-medium">Boleta #{b.id}</p>
                            <p className="text-xs text-muted-foreground">
                              {fmtDate(b.creado_en)} · {b.tipo_pago}
                            </p>
                          </div>
                          <span className="font-mono-data text-sm font-medium">{fmt(b.total)}</span>
                        </div>
                      ))}
                    </div>

                    <div className="rounded-md bg-muted/50 p-3 space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {boletasSeleccionadas.size} boleta{boletasSeleccionadas.size !== 1 ? 's' : ''} seleccionada{boletasSeleccionadas.size !== 1 ? 's' : ''}
                        </span>
                        <span className="font-mono-data font-bold text-primary">{fmt(totalSeleccionado)}</span>
                      </div>
                      {!clienteSeleccionado.ruc && (
                        <p className="text-xs text-destructive">
                          ⚠ Este cliente no tiene RUC. No se puede emitir factura.
                        </p>
                      )}
                      <Button
                        className="w-full"
                        disabled={submitting || boletasSeleccionadas.size === 0 || !clienteSeleccionado.ruc}
                        onClick={handleGenerarFactura}
                      >
                        {submitting ? (
                          <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Generando...</>
                        ) : (
                          <><Printer className="mr-2 h-4 w-4" />Generar e Imprimir Factura</>
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ═══════════════ TAB: FACTURAS EMITIDAS ═══════════════ */}
        <TabsContent value="emitidas" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Facturas Emitidas
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loadingEmitidas ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : facturasEmitidas.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No hay facturas emitidas aún</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Número</TableHead>
                      <TableHead>Cliente</TableHead>
                      <TableHead>RUC</TableHead>
                      <TableHead className="text-center">Boletas</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {facturasEmitidas.map((f) => (
                      <TableRow key={f.id}>
                        <TableCell className="font-mono font-medium">{f.numero}</TableCell>
                        <TableCell>{f.cliente_nombre}</TableCell>
                        <TableCell className="font-mono text-sm">{f.cliente_ruc}</TableCell>
                        <TableCell className="text-center">
                          <Badge variant="secondary">{f.boletas_count}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono-data">{fmt(f.total)}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{fmtDate(f.creado_en)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 justify-end">
                            {facturasFE[f.id] && <EstadoFE documento={facturasFE[f.id]} />}
                            {modulos.fe && (
                              <Button variant={electronicaPorDefecto ? 'default' : 'outline'} size="sm" onClick={() => setGrupalFE(f)}
                                      data-testid={`fe-grupal-${f.id}`}>
                                <FileText className="h-3 w-3 mr-1" />
                                Electrónica
                              </Button>
                            )}
                            <Button variant="outline" size="sm" onClick={() => handleReimprimir(f.id, f.numero)}
                                    title="Hoja preimpresa de la SET en la impresora matricial (Epson LX-350)">
                              <Printer className="h-3 w-3 mr-1" />
                              {modulos.fe ? 'Preimpresa' : 'Imprimir'}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!grupalFE} onOpenChange={(abierto) => { if (!abierto) { setGrupalFE(null); cargarEstadosFE(); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Factura electrónica · {grupalFE?.numero}</DialogTitle>
            <DialogDescription>{grupalFE?.cliente_nombre} · {grupalFE?.boletas_count} boletas en una sola factura</DialogDescription>
          </DialogHeader>
          {grupalFE && <PanelFacturaElectronica grupalId={grupalFE.id} />}
        </DialogContent>
      </Dialog>

      {/* Área oculta para render de impresión */}
      <div style={{ position: 'fixed', left: '-9999px', top: 0, pointerEvents: 'none' }}>
        <FacturaPrint ref={facturaRef} data={facturaImpresionData} />
      </div>

      {/* Modal: selección tipo de factura */}
      <Dialog open={modalTipoPago} onOpenChange={setModalTipoPago}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>¿Cómo desea generar la factura?</DialogTitle>
            <DialogDescription>
              Seleccione si desea cobrar los créditos pendientes o solo agrupar las boletas para enviarle al cliente.
            </DialogDescription>
          </DialogHeader>
          {hayMixto && (
            <div className="rounded-md bg-amber-50 border border-amber-200 text-amber-800 px-3 py-2 text-sm">
              ⚠ Tiene boletas de distintos métodos de pago seleccionadas. La opción <strong>A Crédito</strong> no está disponible — solo puede usarse cuando todas las boletas son de crédito.
            </div>
          )}
          <div className="grid grid-cols-2 gap-3 py-2">
            <button
              onClick={() => confirmarGenerarFactura(true)}
              className="flex flex-col items-center gap-2 rounded-lg border-2 border-primary/30 bg-primary/5 hover:border-primary hover:bg-primary/10 p-4 transition-colors text-center"
            >
              <Banknote className="h-8 w-8 text-primary" />
              <span className="font-semibold text-sm">Al Contado</span>
              <span className="text-xs text-muted-foreground">Cobra los créditos pendientes asociados a las boletas</span>
            </button>
            <button
              disabled={!todasCredito}
              onClick={() => todasCredito && confirmarGenerarFactura(false)}
              className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-colors text-center ${
                todasCredito
                  ? 'border-orange-300 bg-orange-50 hover:border-orange-500 hover:bg-orange-100 cursor-pointer'
                  : 'border-muted bg-muted/30 opacity-50 cursor-not-allowed'
              }`}
            >
              <CreditCard className="h-8 w-8 text-orange-500" />
              <span className="font-semibold text-sm">A Crédito</span>
              <span className="text-xs text-muted-foreground">Agrupa las boletas sin cobrar el crédito. El cliente lo pagará luego.</span>
              {!todasCredito && (
                <span className="text-xs text-destructive font-medium">Solo disponible si todas las boletas son de crédito</span>
              )}
            </button>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalTipoPago(false)}>Cancelar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Facturas;
