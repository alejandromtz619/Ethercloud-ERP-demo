import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
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
import { Warehouse, Plus, Loader2, Search, ArrowRight, Bell, Package, Minus, Trash2, History, ShoppingCart, CreditCard, Building2, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import { DatePickerInput } from '../components/ui/date-picker-input';
import EntradaStockDialog from '../components/EntradaStockDialog';
import SalidaStockDialog from '../components/SalidaStockDialog';
import ProductoCombobox from '../components/ProductoCombobox';

const STOCK_POR_PAGINA = 100;

// Las ventas se registran como SALIDA con referencia_tipo 'venta'; el resto de
// salidas son bajas manuales (rotura, robo, etc.).
const clasificarMovimiento = (mov) => {
  if (mov.tipo === 'VENTA' || (mov.tipo === 'SALIDA' && mov.referencia_tipo === 'venta')) return 'VENTA';
  if (mov.tipo === 'SALIDA') return 'BAJA';
  return mov.tipo;
};

const Stock = () => {
  const { api, empresa, userPermisos } = useApp();
  // Página actual del inventario (GET /stock/buscar): filtros y paginación en el servidor
  const [stock, setStock] = useState({ items: [], total: 0 });
  const [cargandoMas, setCargandoMas] = useState(false);
  const [almacenes, setAlmacenes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [salidaDialogOpen, setSalidaDialogOpen] = useState(false);
  const [traspasoDialogOpen, setTraspasoDialogOpen] = useState(false);
  const [almacenDialogOpen, setAlmacenDialogOpen] = useState(false);
  const [selectedAlmacen, setSelectedAlmacen] = useState('');
  const [search, setSearch] = useState('');
  const [searchId, setSearchId] = useState('');
  const [searchCodigo, setSearchCodigo] = useState('');
  
  const [historialDialogOpen, setHistorialDialogOpen] = useState(false);
  const [historialProducto, setHistorialProducto] = useState(null);
  const [historialData, setHistorialData] = useState([]);
  const [historialLoading, setHistorialLoading] = useState(false);
  const [historialFiltroTipo, setHistorialFiltroTipo] = useState('TODOS'); // Filtro por tipo de movimiento

  const [traspasoForm, setTraspasoForm] = useState({
    producto_id: '',
    almacen_origen_id: '',
    almacen_destino_id: '',
    cantidad: ''
  });

  const [almacenForm, setAlmacenForm] = useState({
    nombre: '',
    ubicacion: ''
  });

  const [traspasoProducto, setTraspasoProducto] = useState(null);
  // Unidades por almacén para las tarjetas de arriba (sumadas en el servidor)
  const [totalesAlmacen, setTotalesAlmacen] = useState({});
  // Filtros de texto aplicados con un pequeño retraso para no consultar en cada tecla
  const [filtros, setFiltros] = useState({ nombre: '', id: '', codigo: '' });
  const [proveedores, setProveedores] = useState([]);

  const cargarStock = async (offset = 0) => {
    if (!empresa?.id) return;
    const params = new URLSearchParams({ empresa_id: empresa.id, limit: STOCK_POR_PAGINA, offset });
    if (selectedAlmacen) params.set('almacen_id', selectedAlmacen);
    if (filtros.nombre) params.set('nombre', filtros.nombre);
    if (filtros.codigo) params.set('codigo', filtros.codigo);
    if (filtros.id) {
      if (!/^\d+$/.test(filtros.id)) {
        setStock({ items: [], total: 0 });
        return;
      }
      params.set('producto_id', filtros.id);
    }
    const data = await api(`/stock/buscar?${params}`);
    setStock(prev => (offset > 0 ? { ...data, items: [...prev.items, ...data.items] } : data));
  };

  const fetchCatalogos = async () => {
    if (!empresa?.id) return;
    try {
      const [almacenesData, proveedoresData, totalesData] = await Promise.all([
        api(`/almacenes?empresa_id=${empresa.id}`),
        api(`/proveedores?empresa_id=${empresa.id}`),
        api(`/stock/totales-por-almacen?empresa_id=${empresa.id}`)
      ]);
      setAlmacenes(almacenesData);
      setProveedores(proveedoresData);
      setTotalesAlmacen(Object.fromEntries(totalesData.map(t => [t.almacen_id, t.total_unidades])));
    } catch (e) {
      toast.error('Error al cargar datos');
    }
  };

  // Recarga todo después de una entrada, salida, traspaso o alerta
  const fetchData = async () => {
    try {
      await Promise.all([fetchCatalogos(), cargarStock(0)]);
    } catch (e) {
      toast.error('Error al cargar stock');
    }
  };

  const cargarMas = async () => {
    setCargandoMas(true);
    try {
      await cargarStock(stock.items.length);
    } catch (e) {
      toast.error('Error al cargar stock');
    } finally {
      setCargandoMas(false);
    }
  };

  useEffect(() => {
    fetchCatalogos();
  }, [empresa?.id]);

  useEffect(() => {
    const t = setTimeout(() => {
      setFiltros({ nombre: search.trim(), id: searchId.trim(), codigo: searchCodigo.trim() });
    }, 300);
    return () => clearTimeout(t);
  }, [search, searchId, searchCodigo]);

  useEffect(() => {
    cargarStock(0)
      .catch(() => toast.error('Error al cargar stock'))
      .finally(() => setLoading(false));
  }, [empresa?.id, selectedAlmacen, filtros]);

  const fetchHistorial = async (productoId, productoNombre) => {
    setHistorialProducto({ id: productoId, nombre: productoNombre });
    setHistorialDialogOpen(true);
    setHistorialLoading(true);
    setHistorialFiltroTipo('TODOS'); // Reset filter when opening
    try {
      const data = await api(`/stock/historial/${productoId}`);
      setHistorialData(data);
    } catch (e) {
      toast.error('Error al cargar historial');
      setHistorialData([]);
    } finally {
      setHistorialLoading(false);
    }
  };

  const formatCurrency = (val) => {
    if (val == null) return '-';
    return 'Gs. ' + Number(val).toLocaleString('es-PY');
  };

  const handleTraspaso = async (e) => {
    e.preventDefault();
    if (!traspasoForm.producto_id || !traspasoForm.almacen_origen_id || 
        !traspasoForm.almacen_destino_id || !traspasoForm.cantidad) {
      toast.error('Complete todos los campos');
      return;
    }

    if (traspasoForm.almacen_origen_id === traspasoForm.almacen_destino_id) {
      toast.error('Los almacenes deben ser diferentes');
      return;
    }

    try {
      await api('/stock/traspaso', {
        method: 'POST',
        body: JSON.stringify({
          producto_id: parseInt(traspasoForm.producto_id),
          almacen_origen_id: parseInt(traspasoForm.almacen_origen_id),
          almacen_destino_id: parseInt(traspasoForm.almacen_destino_id),
          cantidad: parseInt(traspasoForm.cantidad)
        })
      });
      toast.success('Traspaso realizado');
      setTraspasoDialogOpen(false);
      setTraspasoForm({ producto_id: '', almacen_origen_id: '', almacen_destino_id: '', cantidad: '' });
      setTraspasoProducto(null);
      fetchData();
    } catch (e) {
      toast.error(e.message || 'Error al realizar traspaso');
    }
  };

  const handleCrearAlmacen = async (e) => {
    e.preventDefault();
    if (!almacenForm.nombre) {
      toast.error('El nombre es requerido');
      return;
    }

    try {
      await api('/almacenes', {
        method: 'POST',
        body: JSON.stringify({ ...almacenForm, empresa_id: empresa.id })
      });
      toast.success('Almacén creado');
      setAlmacenDialogOpen(false);
      setAlmacenForm({ nombre: '', ubicacion: '' });
      fetchData();
    } catch (e) {
      toast.error('Error al crear almacén');
    }
  };

  const handleSetAlerta = async (stockId, alertaMinima) => {
    try {
      await api(`/stock/${stockId}/alerta?alerta_minima=${alertaMinima}`, { method: 'PUT' });
      toast.success('Alerta configurada');
      fetchData();
    } catch (e) {
      toast.error('Error al configurar alerta');
    }
  };

  const filteredStock = stock.items;
  const hayFiltros = Boolean(search || searchId || searchCodigo);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="stock-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Stock / Inventario</h1>
          <p className="text-muted-foreground">Gestión de inventario multi-almacén</p>
        </div>
        <div className="flex gap-2">
          {/* Crear Almacén */}
          <Dialog open={almacenDialogOpen} onOpenChange={setAlmacenDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Plus className="mr-2 h-4 w-4" />
                Almacén
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogDescription className="hidden">Formulario para crear un nuevo almacén</DialogDescription>
              <DialogHeader>
                <DialogTitle>Nuevo Almacén</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCrearAlmacen} className="space-y-4">
                <div>
                  <Label>Nombre *</Label>
                  <Input
                    value={almacenForm.nombre}
                    onChange={(e) => setAlmacenForm({...almacenForm, nombre: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Ubicación</Label>
                  <Input
                    value={almacenForm.ubicacion}
                    onChange={(e) => setAlmacenForm({...almacenForm, ubicacion: e.target.value})}
                  />
                </div>
                <Button type="submit" className="w-full">Crear Almacén</Button>
              </form>
            </DialogContent>
          </Dialog>

          {/* Traspaso */}
          {userPermisos.includes('stock.traspasar') && (
            <Dialog open={traspasoDialogOpen} onOpenChange={setTraspasoDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline">
                  <ArrowRight className="mr-2 h-4 w-4" />
                  Traspaso
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogDescription className="hidden">Formulario para traspasar stock entre almacenes</DialogDescription>
              <DialogHeader>
                <DialogTitle>Traspaso entre Almacenes</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleTraspaso} className="space-y-4">
                <div>
                  <Label>Producto</Label>
                  <ProductoCombobox
                    value={traspasoProducto}
                    onChange={(p) => {
                      setTraspasoProducto(p);
                      setTraspasoForm({ ...traspasoForm, producto_id: p.id.toString() });
                    }}
                  />
                </div>
                <div>
                  <Label>Almacén Origen</Label>
                  <Select value={traspasoForm.almacen_origen_id} onValueChange={(v) => setTraspasoForm({...traspasoForm, almacen_origen_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      {almacenes.map(a => (
                        <SelectItem key={a.id} value={a.id.toString()}>{a.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Almacén Destino</Label>
                  <Select value={traspasoForm.almacen_destino_id} onValueChange={(v) => setTraspasoForm({...traspasoForm, almacen_destino_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      {almacenes.map(a => (
                        <SelectItem key={a.id} value={a.id.toString()}>{a.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Cantidad</Label>
                  <Input
                    type="number"
                    min="1"
                    value={traspasoForm.cantidad}
                    onChange={(e) => setTraspasoForm({...traspasoForm, cantidad: e.target.value})}
                  />
                </div>
                <Button type="submit" className="w-full">Realizar Traspaso</Button>
              </form>
            </DialogContent>
          </Dialog>
          )}

          {/* Entrada Stock */}
          {userPermisos.includes('stock.entrada') && (
            <>
              <Button data-testid="entrada-stock-btn" onClick={() => setDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Entrada
              </Button>
              <EntradaStockDialog open={dialogOpen} onOpenChange={setDialogOpen} onSuccess={fetchData} />
            </>
          )}

          {/* Salida Stock */}
          {userPermisos.includes('stock.salida') && (
            <>
              <Button variant="destructive" data-testid="salida-stock-btn" onClick={() => setSalidaDialogOpen(true)}>
                <Minus className="mr-2 h-4 w-4" />
                Salida
              </Button>
              <SalidaStockDialog open={salidaDialogOpen} onOpenChange={setSalidaDialogOpen} onSuccess={fetchData} />
            </>
          )}
        </div>
      </div>

      {/* Almacenes Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {almacenes.map((almacen) => {
          const totalItems = totalesAlmacen[almacen.id] || 0;
          return (
            <Card 
              key={almacen.id} 
              className={cn(
                "cursor-pointer transition-all",
                selectedAlmacen === almacen.id.toString() && "ring-2 ring-primary"
              )}
              onClick={() => setSelectedAlmacen(
                selectedAlmacen === almacen.id.toString() ? '' : almacen.id.toString()
              )}
            >
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <Warehouse className="h-8 w-8 text-primary" />
                  <div>
                    <p className="font-medium">{almacen.nombre}</p>
                    <p className="text-sm text-muted-foreground">{totalItems} items</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Stock Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Inventario {selectedAlmacen && `- ${almacenes.find(a => a.id.toString() === selectedAlmacen)?.nombre}`}
              </CardTitle>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nombre..."
                  className="pl-9"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Filtros:</span>
              <div className="relative">
                <Input
                  placeholder="ID..."
                  className="pl-3 pr-7 h-8 w-24 text-sm font-mono"
                  type="number"
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value)}
                />
                {searchId && (
                  <button
                    onClick={() => setSearchId('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
              <div className="relative">
                <Input
                  placeholder="Cód. barra..."
                  className="pl-3 pr-7 h-8 w-44 text-sm font-mono"
                  value={searchCodigo}
                  onChange={(e) => setSearchCodigo(e.target.value)}
                />
                {searchCodigo && (
                  <button
                    onClick={() => setSearchCodigo('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
              {(search || searchId || searchCodigo) && (
                <button
                  onClick={() => { setSearch(''); setSearchId(''); setSearchCodigo(''); }}
                  className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1"
                >
                  <X className="h-3 w-3" /> Limpiar
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredStock.length === 0 ? (
            <div className="text-center py-12">
              <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                {hayFiltros ? 'Ningún producto coincide con los filtros' : 'No hay stock registrado'}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="table-compact">
                  <TableHead>Producto</TableHead>
                  <TableHead>Almacén</TableHead>
                  <TableHead>Cantidad</TableHead>
                  <TableHead>Alerta Mínima</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredStock.map((item) => {
                  const isBajo = item.alerta_minima && item.cantidad <= item.alerta_minima;
                  return (
                    <TableRow key={item.id} className={cn(isBajo && "bg-red-50 dark:bg-red-900/10")}>
                      <TableCell className="font-medium">{item.producto_nombre}</TableCell>
                      <TableCell>{item.almacen_nombre}</TableCell>
                      <TableCell className="font-mono-data font-bold">{item.cantidad}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            className="w-20 h-8"
                            defaultValue={item.alerta_minima || ''}
                            onBlur={(e) => {
                              if (e.target.value) {
                                handleSetAlerta(item.id, parseInt(e.target.value));
                              }
                            }}
                          />
                          <Bell className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </TableCell>
                      <TableCell>
                        {isBajo ? (
                          <Badge variant="destructive">Stock Bajo</Badge>
                        ) : (
                          <Badge className="badge-success">OK</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 gap-1 text-muted-foreground hover:text-foreground"
                          onClick={() => fetchHistorial(item.producto_id, item.producto_nombre)}
                          title="Ver historial de movimientos"
                        >
                          <History className="h-4 w-4" />
                          Historial
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
          {filteredStock.length > 0 && (
            <div className="flex items-center justify-between gap-3 pt-4 text-xs text-muted-foreground">
              <span>
                Mostrando {filteredStock.length.toLocaleString('es-PY')} de {stock.total.toLocaleString('es-PY')}
              </span>
              {filteredStock.length < stock.total && (
                <Button size="sm" variant="outline" onClick={cargarMas} disabled={cargandoMas} className="gap-1.5">
                  {cargandoMas && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Cargar más
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>
      {/* Historial Dialog */}
      <Dialog open={historialDialogOpen} onOpenChange={setHistorialDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[88vh] overflow-y-auto">
          <DialogDescription className="hidden">Historial de movimientos del producto</DialogDescription>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Historial &mdash; {historialProducto?.nombre}
            </DialogTitle>
          </DialogHeader>
          
          {/* Filtro por tipo de movimiento */}
          {!historialLoading && historialData.length > 0 && (
            <div className="flex items-center gap-3 pb-3 border-b">
              <Label className="text-sm font-medium">Filtrar por tipo:</Label>
              <Select value={historialFiltroTipo} onValueChange={setHistorialFiltroTipo}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="TODOS">Todos los movimientos</SelectItem>
                  <SelectItem value="ENTRADA">Entradas</SelectItem>
                  <SelectItem value="VENTA">Ventas</SelectItem>
                  <SelectItem value="BAJA">Bajas</SelectItem>
                  <SelectItem value="TRASPASO">Traspasos</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground ml-auto">
                {historialFiltroTipo === 'TODOS' 
                  ? `${historialData.length} movimientos totales`
                  : `${historialData.filter(m => clasificarMovimiento(m) === historialFiltroTipo).length} de ${historialData.length}`
                }
              </span>
            </div>
          )}

          {historialLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : historialData.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No hay movimientos registrados para este producto
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Almacén</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Cant. Restante</TableHead>
                  <TableHead className="text-right">Costo Unit.</TableHead>
                  <TableHead className="text-right">CPP</TableHead>
                  <TableHead className="text-right">Total Compra</TableHead>
                  <TableHead>Condición</TableHead>
                  <TableHead>Proveedor</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Notas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historialData
                  .filter(mov => historialFiltroTipo === 'TODOS' || clasificarMovimiento(mov) === historialFiltroTipo)
                  .map((mov) => {
                    const tipoColor = {
                      ENTRADA: 'text-green-600 dark:text-green-400',
                      BAJA: 'text-red-600 dark:text-red-400',
                      TRASPASO: 'text-blue-600 dark:text-blue-400',
                      VENTA: 'text-amber-500 dark:text-amber-400',
                    };
                    const tipoLabel = {
                      ENTRADA: 'Entrada',
                      BAJA: 'Baja',
                      TRASPASO: 'Traspaso',
                      VENTA: 'Venta',
                    };
                    const tipoMov = clasificarMovimiento(mov);
                    
                    // Determinar estado FIFO
                    const cantidadRestante = mov.cantidad_restante ?? null;
                    const isAgotado = cantidadRestante !== null && cantidadRestante === 0;
                    const isActivo = cantidadRestante !== null && cantidadRestante > 0;
                    
                    return (
                      <TableRow key={mov.id} className={isAgotado ? 'opacity-60' : ''}>
                        <TableCell className="text-xs whitespace-nowrap">
                          {mov.creado_en ? new Date(mov.creado_en).toLocaleDateString('es-PY', {
                            day: '2-digit', month: '2-digit', year: 'numeric',
                            hour: '2-digit', minute: '2-digit',
                            timeZone: 'America/Asuncion'
                          }) : '-'}
                        </TableCell>
                        <TableCell className={cn('font-semibold text-xs', tipoColor[tipoMov])}>
                          {tipoLabel[tipoMov] || mov.tipo}
                        </TableCell>
                        <TableCell className="text-xs">{mov.almacen_nombre || '-'}</TableCell>
                        <TableCell className="text-right font-mono font-bold">
                          {mov.cantidad > 0 ? `+${mov.cantidad}` : mov.cantidad}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold">
                          {cantidadRestante !== null ? (
                            <span className={isActivo ? 'text-green-600' : 'text-muted-foreground line-through'}>
                              {cantidadRestante}
                            </span>
                          ) : mov.tipo === 'ENTRADA' && mov.referencia_tipo !== 'ANULACION_VENTA' ? (
                            <span className="text-muted-foreground text-[10px] font-normal" title="Entrada anterior al seguimiento FIFO">sin FIFO</span>
                          ) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs">
                          {mov.costo_unitario != null ? formatCurrency(mov.costo_unitario) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs font-semibold text-blue-600">
                          {mov.costo_ponderado != null ? formatCurrency(mov.costo_ponderado) : '-'}
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs font-semibold">
                          {mov.total_compra != null ? formatCurrency(mov.total_compra) : '-'}
                        </TableCell>
                        <TableCell>
                          {mov.condicion_pago ? (
                            <Badge variant={mov.condicion_pago === 'credito' ? 'outline' : 'secondary'} className="text-xs capitalize">
                              {mov.condicion_pago === 'credito' ? (
                                <><CreditCard className="h-3 w-3 mr-1" />Crédito</>
                              ) : (
                                <><ShoppingCart className="h-3 w-3 mr-1" />Contado</>
                              )}
                            </Badge>
                          ) : '-'}
                        </TableCell>
                        <TableCell className="text-xs">
                          {mov.proveedor_nombre ? (
                            <span className="flex items-center gap-1">
                              <Building2 className="h-3 w-3 opacity-60" />
                              {mov.proveedor_nombre}
                            </span>
                          ) : '-'}
                        </TableCell>
                        <TableCell>
                          {cantidadRestante !== null && mov.tipo === 'ENTRADA' ? (
                            <Badge variant={isActivo ? 'default' : 'secondary'} className="text-xs">
                              {isActivo ? 'Activo' : 'Agotado'}
                            </Badge>
                          ) : '-'}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate">
                          {mov.notas || '-'}
                        </TableCell>
                      </TableRow>
                    );
                  })}
              </TableBody>
            </Table>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Stock;
