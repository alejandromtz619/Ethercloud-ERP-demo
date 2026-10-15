import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '../components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Textarea } from '../components/ui/textarea';
import { DatePickerInput } from '../components/ui/date-picker-input';
import {
  FileSpreadsheet, Plus, Loader2, X, ChevronsUpDown, Check, Trash2,
  Download, FileText, Package, Eye
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import { resolverImagenUrl } from '../lib/imagenes';
import ProductoCombobox from '../components/ProductoCombobox';
import ClienteCombobox from '../components/ClienteCombobox';

// `producto` guarda el producto elegido (lo devuelve el buscador del servidor)
const emptyItem = { producto_id: '', producto: null, cantidad: '1', precio_unitario: '' };

const PRESUPUESTOS_POR_PAGINA = 100;

const Presupuestos = () => {
  const { api, empresa, user, hasPermission, API_URL, token } = useApp();
  const [presupuestos, setPresupuestos] = useState([]);
  const [hayMas, setHayMas] = useState(false);
const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);

  // Filtros
  const [filtroNumero, setFiltroNumero] = useState('');
  const [filtroClienteId, setFiltroClienteId] = useState('');
  const [filtroMontoDesde, setFiltroMontoDesde] = useState('');
  const [filtroMontoHasta, setFiltroMontoHasta] = useState('');
  const [filtroFechaDesde, setFiltroFechaDesde] = useState('');
  const [filtroFechaHasta, setFiltroFechaHasta] = useState('');

  // Formulario de creación
  const [clienteId, setClienteId] = useState('');
  const [notas, setNotas] = useState('');
  const [items, setItems] = useState([{ ...emptyItem }]);
  // Clientes elegidos (se buscan en el servidor, ya no se descarga la lista completa)
  const [clienteSel, setClienteSel] = useState(null);
  const [filtroCliente, setFiltroCliente] = useState(null);

  // Visor de PDF en el sistema
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerLoading, setViewerLoading] = useState(false);
  const [viewerUrl, setViewerUrl] = useState(null);
  const [viewerNumero, setViewerNumero] = useState('');

  // La lista se pide de a páginas: con miles de presupuestos, dibujarlos todos trababa la pantalla
  const fetchPresupuestos = async (offset = 0) => {
    if (!empresa?.id) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ empresa_id: empresa.id, limit: PRESUPUESTOS_POR_PAGINA, offset });
      if (filtroNumero) params.append('numero', filtroNumero);
      if (filtroClienteId) params.append('cliente_id', filtroClienteId);
      if (filtroMontoDesde) params.append('monto_desde', filtroMontoDesde);
      if (filtroMontoHasta) params.append('monto_hasta', filtroMontoHasta);
      if (filtroFechaDesde) params.append('fecha_desde', filtroFechaDesde);
      if (filtroFechaHasta) params.append('fecha_hasta', filtroFechaHasta);
      const data = await api(`/presupuestos?${params.toString()}`);
      setPresupuestos(prev => (offset > 0 ? [...prev, ...data] : data));
      setHayMas(data.length === PRESUPUESTOS_POR_PAGINA);
    } catch (e) {
      toast.error('Error al cargar presupuestos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPresupuestos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresa?.id, filtroNumero, filtroClienteId, filtroMontoDesde, filtroMontoHasta, filtroFechaDesde, filtroFechaHasta]);

  const resetForm = () => {
    setClienteId('');
    setClienteSel(null);
setNotas('');
    setItems([{ ...emptyItem }]);
  };

  const addItemRow = () => setItems([...items, { ...emptyItem }]);
  const removeItemRow = (idx) => setItems(items.filter((_, i) => i !== idx));
  const updateItem = (idx, patch) => {
    setItems(items.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  };

  const precioDe = (it) => {
    if (it.precio_unitario !== '' && it.precio_unitario != null) return Number(it.precio_unitario);
    return it.producto ? Number(it.producto.precio_venta) : 0;
  };

  const totalPresupuesto = items.reduce((sum, it) => {
    const cantidad = parseInt(it.cantidad) || 0;
    return sum + precioDe(it) * cantidad;
  }, 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!clienteId) {
      toast.error('Seleccione un cliente');
      return;
    }
    const itemsValidos = items.filter(it => it.producto_id && parseInt(it.cantidad) > 0);
    if (itemsValidos.length === 0) {
      toast.error('Agregue al menos un producto con cantidad válida');
      return;
    }

    setSubmitting(true);
    try {
      await api('/presupuestos', {
        method: 'POST',
        body: JSON.stringify({
          empresa_id: empresa.id,
          cliente_id: parseInt(clienteId),
          usuario_id: user.id,
          notas: notas || null,
          items: itemsValidos.map(it => ({
            producto_id: parseInt(it.producto_id),
            cantidad: parseInt(it.cantidad),
            precio_venta_unitario: it.precio_unitario !== '' && it.precio_unitario != null ? Number(it.precio_unitario) : null
          }))
        })
      });
      toast.success('Presupuesto creado');
      setDialogOpen(false);
      resetForm();
      fetchPresupuestos();
    } catch (e) {
      toast.error(e.message || 'Error al crear presupuesto');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id, numero) => {
    if (!window.confirm(`¿Eliminar el presupuesto ${numero}? Esta acción no se puede deshacer.`)) return;
    try {
      await api(`/presupuestos/${id}`, { method: 'DELETE' });
      toast.success('Presupuesto eliminado');
      fetchPresupuestos();
    } catch (e) {
      toast.error(e.message || 'Error al eliminar presupuesto');
    }
  };

  const handleDownload = async (id, numero, formato) => {
    const key = `${id}_${formato}`;
    setDownloadingId(key);
    try {
      const response = await fetch(`${API_URL}/presupuestos/${id}/${formato}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        throw new Error('Error al generar el documento');
      }
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${numero}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (e) {
      toast.error(e.message || 'Error al descargar');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleView = async (id, numero) => {
    setViewerLoading(true);
    setViewerNumero(numero);
    setViewerOpen(true);
    try {
      const response = await fetch(`${API_URL}/presupuestos/${id}/pdf`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!response.ok) {
        throw new Error('Error al generar el documento');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      setViewerUrl(url);
    } catch (e) {
      toast.error(e.message || 'Error al visualizar el presupuesto');
      setViewerOpen(false);
    } finally {
      setViewerLoading(false);
    }
  };

  const closeViewer = (open) => {
    setViewerOpen(open);
    if (!open && viewerUrl) {
      window.URL.revokeObjectURL(viewerUrl);
      setViewerUrl(null);
    }
  };

  const formatCurrency = (val) => 'Gs. ' + Number(val || 0).toLocaleString('es-PY');

  const formatFecha = (iso) => {
    if (!iso) return '-';
    try {
      return new Date(iso).toLocaleDateString('es-PY', { timeZone: 'America/Asuncion' });
    } catch {
      return '-';
    }
  };

  const hayFiltrosActivos = filtroNumero || filtroClienteId || filtroMontoDesde || filtroMontoHasta || filtroFechaDesde || filtroFechaHasta;
  const limpiarFiltros = () => {
    setFiltroNumero('');
    setFiltroClienteId('');
    setFiltroCliente(null);
setFiltroMontoDesde('');
    setFiltroMontoHasta('');
    setFiltroFechaDesde('');
    setFiltroFechaHasta('');
  };

  if (loading && presupuestos.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="presupuestos-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Presupuestos</h1>
          <p className="text-muted-foreground">Cotizaciones comerciales para clientes — no afectan el stock</p>
        </div>
        {hasPermission('presupuestos.crear') && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Presupuesto
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
              <DialogDescription className="hidden">Formulario para crear un presupuesto</DialogDescription>
              <DialogHeader>
                <DialogTitle>Nuevo Presupuesto</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label>Cliente *</Label>
                  <ClienteCombobox
                    value={clienteSel}
                    onChange={(c) => {
                      setClienteSel(c);
                      setClienteId(c.id.toString());
                    }}
                    placeholder="Seleccionar cliente..."
                    contentClassName="w-[420px]"
                  />
                </div>

                <div className="space-y-3">
                  <Label>Productos *</Label>
                  {items.map((item, idx) => {
                    const producto = item.producto;
                    return (
                      <div key={idx} className="flex items-start gap-2 border rounded-lg p-2">
                        {producto?.imagen_url ? (
                          <img
                            src={resolverImagenUrl(producto.imagen_url)}
                            alt=""
                            className="w-10 h-10 rounded object-cover shrink-0"
                            loading="lazy"
                            decoding="async"
                            referrerPolicy="no-referrer"
                            onError={(e) => { e.currentTarget.style.visibility = 'hidden'; }}
                          />
                        ) : (
                          <div className="w-10 h-10 rounded bg-muted flex items-center justify-center shrink-0">
                            <Package className="h-5 w-5 text-muted-foreground" />
                          </div>
                        )}
                        <div className="flex-1 space-y-1">
                          <ProductoCombobox
                            value={producto}
                            onChange={(p) => updateItem(idx, {
                              producto_id: p.id.toString(),
                              producto: p,
                              precio_unitario: p.precio_venta?.toString() || ''
                            })}
                            renderDetalle={(p) => (
                              <span className="text-xs text-muted-foreground">{formatCurrency(p.precio_venta)}</span>
                            )}
                          />
                          {producto && (
                            <div className="flex items-center gap-3 pt-1">
                              <div>
                                <Label className="text-xs text-muted-foreground">Cantidad</Label>
                                <Input
                                  type="number"
                                  min="1"
                                  className="w-20 h-8"
                                  value={item.cantidad}
                                  onChange={(e) => updateItem(idx, { cantidad: e.target.value })}
                                />
                              </div>
                              <div>
                                <Label className="text-xs text-muted-foreground">Precio unit.</Label>
                                <Input
                                  type="number"
                                  min="0"
                                  className="w-28 h-8"
                                  value={item.precio_unitario}
                                  disabled={!hasPermission('ventas.modificar_precio')}
                                  onChange={(e) => updateItem(idx, { precio_unitario: e.target.value })}
                                />
                              </div>
                              <p className="text-xs text-muted-foreground pt-4">
                                Subtotal: {formatCurrency(precioDe(item) * (parseInt(item.cantidad) || 0))}
                              </p>
                            </div>
                          )}
                        </div>
                        {items.length > 1 && (
                          <Button type="button" variant="ghost" size="icon" onClick={() => removeItemRow(idx)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    );
                  })}
                  <Button type="button" variant="outline" size="sm" onClick={addItemRow}>
                    <Plus className="mr-2 h-4 w-4" />
                    Agregar producto
                  </Button>
                </div>

                <div>
                  <Label>Notas (opcional)</Label>
                  <Textarea value={notas} onChange={(e) => setNotas(e.target.value)} />
                </div>

                <div className="flex items-center justify-between border-t pt-3">
                  <span className="text-sm text-muted-foreground">Total del presupuesto</span>
                  <span className="text-lg font-bold">{formatCurrency(totalPresupuesto)}</span>
                </div>

                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={submitting}>
                    {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                    Crear Presupuesto
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3">
            <CardTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              Presupuestos ({presupuestos.length}{hayMas ? '+' : ''})
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Filtros:</span>
              <Input
                placeholder="presupuesto-001..."
                className="h-8 w-40 text-sm font-mono"
                value={filtroNumero}
                onChange={(e) => setFiltroNumero(e.target.value)}
              />
              <div className="flex items-center gap-1">
                <ClienteCombobox
                  value={filtroCliente}
                  onChange={(c) => {
                    setFiltroCliente(c);
                    setFiltroClienteId(c.id.toString());
                  }}
                  placeholder="Todos los clientes"
                  className="h-8 w-48 text-sm"
                  contentClassName="w-[320px]"
                />
                {filtroClienteId && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    title="Todos los clientes"
                    onClick={() => {
                      setFiltroClienteId('');
                      setFiltroCliente(null);
                    }}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
              <Input
                type="number"
                placeholder="Monto desde"
                className="h-8 w-32 text-sm"
                value={filtroMontoDesde}
                onChange={(e) => setFiltroMontoDesde(e.target.value)}
              />
              <Input
                type="number"
                placeholder="Monto hasta"
                className="h-8 w-32 text-sm"
                value={filtroMontoHasta}
                onChange={(e) => setFiltroMontoHasta(e.target.value)}
              />
              <div className="w-36">
                <DatePickerInput value={filtroFechaDesde} onChange={setFiltroFechaDesde} placeholder="Fecha desde" />
              </div>
              <div className="w-36">
                <DatePickerInput value={filtroFechaHasta} onChange={setFiltroFechaHasta} placeholder="Fecha hasta" />
              </div>
              {hayFiltrosActivos && (
                <button
                  onClick={limpiarFiltros}
                  className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1"
                >
                  <X className="h-3 w-3" /> Limpiar filtros
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {presupuestos.length === 0 ? (
            <div className="text-center py-12">
              <FileSpreadsheet className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No hay presupuestos registrados</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="table-compact">
                  <TableHead>Número</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Total</TableHead>
                  <TableHead className="w-32">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {presupuestos.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell className="font-mono text-sm font-bold">{p.numero}</TableCell>
                    <TableCell>{p.cliente_nombre}</TableCell>
                    <TableCell>{formatFecha(p.creado_en)}</TableCell>
                    <TableCell className="font-mono-data">{formatCurrency(p.total)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Ver presupuesto"
                          onClick={() => handleView(p.id, p.numero)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Descargar PDF"
                          disabled={downloadingId === `${p.id}_pdf`}
                          onClick={() => handleDownload(p.id, p.numero, 'pdf')}
                        >
                          {downloadingId === `${p.id}_pdf` ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <FileText className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Descargar Excel"
                          disabled={downloadingId === `${p.id}_xlsx`}
                          onClick={() => handleDownload(p.id, p.numero, 'xlsx')}
                        >
                          {downloadingId === `${p.id}_xlsx` ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                        </Button>
                        {hasPermission('presupuestos.eliminar') && (
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(p.id, p.numero)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {hayMas && (
            <div className="flex justify-center pt-4">
              <Button size="sm" variant="outline" onClick={() => fetchPresupuestos(presupuestos.length)} disabled={loading} className="gap-1.5">
                {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Cargar más
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={viewerOpen} onOpenChange={closeViewer}>
        <DialogContent className="max-w-4xl h-[90vh] flex flex-col p-0 gap-0">
          <DialogDescription className="hidden">Vista previa del presupuesto en PDF</DialogDescription>
          <DialogHeader className="px-4 py-3 border-b shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {viewerNumero}
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 bg-muted">
            {viewerLoading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : viewerUrl ? (
              <iframe src={viewerUrl} title={viewerNumero} className="w-full h-full border-0" />
            ) : null}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Presupuestos;
