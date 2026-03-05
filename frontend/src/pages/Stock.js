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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '../components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import { Warehouse, Plus, Loader2, Search, ArrowRight, Bell, Package, Minus, Trash2, Check, ChevronsUpDown, History, ShoppingCart, CreditCard, Building2, AlertTriangle, Calculator, Filter } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import { DatePickerInput } from '../components/ui/date-picker-input';
import { Alert, AlertDescription } from '../components/ui/alert';

const Stock = () => {
  const { api, empresa, userPermisos } = useApp();
  const [stock, setStock] = useState([]);
  const [almacenes, setAlmacenes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [salidaDialogOpen, setSalidaDialogOpen] = useState(false);
  const [stockTotalMap, setStockTotalMap] = useState({});  // producto_id -> total qty across all almacenes
  const [entradaProductoStock, setEntradaProductoStock] = useState(0); // current total stock of selected product
  const [entradaProductoPrecioCosto, setEntradaProductoPrecioCosto] = useState(0); // original precio_costo before this entrada
  const [entradaCPPAplicado, setEntradaCPPAplicado] = useState(null); // CPP value applied to product pricing (separate from real cost)
  const [historialFilter, setHistorialFilter] = useState('ALL'); // 'ALL' | 'ENTRADA' | 'VENTA' | 'BAJA'
  const [traspasoDialogOpen, setTraspasoDialogOpen] = useState(false);
  const [almacenDialogOpen, setAlmacenDialogOpen] = useState(false);
  const [selectedAlmacen, setSelectedAlmacen] = useState('');
  const [search, setSearch] = useState('');
  
  const [entradaForm, setEntradaForm] = useState({
    producto_id: '',
    almacen_id: '',
    cantidad: '',
    proveedor_id: '',
    costo_unitario: '',
    precio_venta: '',
    condicion_pago: 'contado',
    fecha_limite_pago: '',
    notas: ''
  });

  const [historialDialogOpen, setHistorialDialogOpen] = useState(false);
  const [historialProducto, setHistorialProducto] = useState(null);
  const [historialData, setHistorialData] = useState([]);
  const [historialLoading, setHistorialLoading] = useState(false);

  const [salidaForm, setSalidaForm] = useState({
    producto_id: '',
    almacen_id: '',
    cantidad: '',
    motivo: ''
  });

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

  // Popovers state for searchable product selectors
  const [entradaPopoverOpen, setEntradaPopoverOpen] = useState(false);
  const [salidaPopoverOpen, setSalidaPopoverOpen] = useState(false);
  const [traspasoPopoverOpen, setTraspasoPopoverOpen] = useState(false);
  const [productoSearchEntrada, setProductoSearchEntrada] = useState('');
  const [productoSearchSalida, setProductoSearchSalida] = useState('');
  const [productoSearchTraspaso, setProductoSearchTraspaso] = useState('');
  const [proveedores, setProveedores] = useState([]);

  const fetchData = async () => {
    if (!empresa?.id) return;
    try {
      let stockUrl = `/stock?empresa_id=${empresa.id}`;
      if (selectedAlmacen) stockUrl += `&almacen_id=${selectedAlmacen}`;
      
      const [stockData, almacenesData, productosData, proveedoresData, allStockData] = await Promise.all([
        api(stockUrl),
        api(`/almacenes?empresa_id=${empresa.id}`),
        api(`/productos?empresa_id=${empresa.id}`),
        api(`/proveedores?empresa_id=${empresa.id}`),
        api(`/stock?empresa_id=${empresa.id}`)  // unfiltered, for CPP/warning calculations
      ]);
      
      setStock(stockData);
      setAlmacenes(almacenesData);
      setProductos(productosData);
      setProveedores(proveedoresData);

      // Build total stock map across all almacenes
      const map = {};
      for (const s of allStockData) {
        map[s.producto_id] = (map[s.producto_id] || 0) + (s.cantidad || 0);
      }
      setStockTotalMap(map);
    } catch (e) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [empresa?.id, selectedAlmacen]);

  const handleEntrada = async (e) => {
    e.preventDefault();
    if (!entradaForm.producto_id || !entradaForm.almacen_id || !entradaForm.cantidad) {
      toast.error('Complete todos los campos');
      return;
    }
    if (entradaForm.condicion_pago === 'credito' && !entradaForm.proveedor_id) {
      toast.error('Seleccione un proveedor para registrar la deuda a crédito');
      return;
    }

    try {
      const payload = {
        producto_id: parseInt(entradaForm.producto_id),
        almacen_id: parseInt(entradaForm.almacen_id),
        cantidad: parseInt(entradaForm.cantidad),
        tipo: 'ENTRADA',
        proveedor_id: entradaForm.proveedor_id ? parseInt(entradaForm.proveedor_id) : null,
        costo_unitario: entradaForm.costo_unitario ? parseFloat(entradaForm.costo_unitario) : null,
        costo_ponderado: entradaCPPAplicado,
        precio_venta: entradaForm.precio_venta ? parseFloat(entradaForm.precio_venta) : null,
        condicion_pago: entradaForm.condicion_pago || null,
        fecha_limite_pago: entradaForm.fecha_limite_pago || null,
        notas: entradaForm.notas || null
      };
      await api('/stock/entrada', { method: 'POST', body: JSON.stringify(payload) });
      if (entradaForm.condicion_pago === 'credito' && entradaForm.proveedor_id) {
        toast.success('Entrada registrada y deuda enviada al proveedor');
      } else {
        toast.success('Entrada registrada');
      }
      setDialogOpen(false);
      setEntradaForm({ producto_id: '', almacen_id: '', cantidad: '', proveedor_id: '', costo_unitario: '', precio_venta: '', condicion_pago: 'contado', fecha_limite_pago: '', notas: '' });
      setEntradaProductoStock(0);
      setEntradaProductoPrecioCosto(0);
      setEntradaCPPAplicado(null);
      fetchData();
    } catch (e) {
      toast.error('Error al registrar entrada');
    }
  };

  const fetchHistorial = async (productoId, productoNombre) => {
    setHistorialProducto({ id: productoId, nombre: productoNombre });
    setHistorialDialogOpen(true);
    setHistorialLoading(true);
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
      fetchData();
    } catch (e) {
      toast.error(e.message || 'Error al realizar traspaso');
    }
  };

  const handleSalida = async (e) => {
    e.preventDefault();
    if (!salidaForm.producto_id || !salidaForm.almacen_id || !salidaForm.cantidad) {
      toast.error('Complete todos los campos');
      return;
    }

    try {
      await api('/stock/salida', {
        method: 'POST',
        body: JSON.stringify({
          producto_id: parseInt(salidaForm.producto_id),
          almacen_id: parseInt(salidaForm.almacen_id),
          cantidad: parseInt(salidaForm.cantidad),
          motivo: salidaForm.motivo || 'Salida manual'
        })
      });
      toast.success('Salida registrada');
      setSalidaDialogOpen(false);
      setSalidaForm({ producto_id: '', almacen_id: '', cantidad: '', motivo: '' });
      fetchData();
    } catch (e) {
      toast.error(e.message || 'Error al registrar salida');
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

  const filteredStock = stock.filter(s =>
    s.producto_nombre?.toLowerCase().includes(search.toLowerCase())
  );

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
                  <Popover open={traspasoPopoverOpen} onOpenChange={setTraspasoPopoverOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={traspasoPopoverOpen}
                        className="w-full justify-between"
                      >
                        {traspasoForm.producto_id
                          ? productos.find((p) => p.id.toString() === traspasoForm.producto_id)?.nombre
                          : "Buscar producto..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[400px] p-0">
                      <Command shouldFilter={false}>
                        <CommandInput 
                          placeholder="Buscar por nombre o código..." 
                          value={productoSearchTraspaso}
                          onValueChange={setProductoSearchTraspaso}
                        />
                        <CommandEmpty>No se encontró el producto.</CommandEmpty>
                        <CommandGroup className="max-h-64 overflow-auto">
                          {productos
                            .filter(p => 
                              !productoSearchTraspaso || 
                              p.nombre.toLowerCase().includes(productoSearchTraspaso.toLowerCase()) ||
                              p.codigo_barra?.toLowerCase().includes(productoSearchTraspaso.toLowerCase())
                            )
                            .map((p) => (
                              <CommandItem
                                key={p.id}
                                value={p.nombre}
                                onSelect={() => {
                                  setTraspasoForm({...traspasoForm, producto_id: p.id.toString()});
                                  setTraspasoPopoverOpen(false);
                                  setProductoSearchTraspaso('');
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    traspasoForm.producto_id === p.id.toString() ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                <div className="flex flex-col">
                                  <span>{p.nombre}</span>
                                  {p.codigo_barra && (
                                    <span className="text-xs text-muted-foreground">Código: {p.codigo_barra}</span>
                                  )}
                                </div>
                              </CommandItem>
                            ))}
                        </CommandGroup>
                      </Command>
                    </PopoverContent>
                  </Popover>
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
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button data-testid="entrada-stock-btn">
                  <Plus className="mr-2 h-4 w-4" />
                  Entrada
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogDescription className="hidden">Formulario para registrar una entrada de stock</DialogDescription>
              <DialogHeader>
                <DialogTitle>Entrada de Stock</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleEntrada} className="space-y-4">
                <div>
                  <Label>Producto</Label>
                  <Popover open={entradaPopoverOpen} onOpenChange={setEntradaPopoverOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={entradaPopoverOpen}
                        className="w-full justify-between"
                      >
                        {entradaForm.producto_id
                          ? productos.find((p) => p.id.toString() === entradaForm.producto_id)?.nombre
                          : "Buscar producto..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[400px] p-0">
                      <Command shouldFilter={false}>
                        <CommandInput 
                          placeholder="Buscar por nombre o código..." 
                          value={productoSearchEntrada}
                          onValueChange={setProductoSearchEntrada}
                        />
                        <CommandEmpty>No se encontró el producto.</CommandEmpty>
                        <CommandGroup className="max-h-64 overflow-auto">
                          {productos
                            .filter(p => 
                              !productoSearchEntrada || 
                              p.nombre.toLowerCase().includes(productoSearchEntrada.toLowerCase()) ||
                              p.codigo_barra?.toLowerCase().includes(productoSearchEntrada.toLowerCase())
                            )
                            .map((p) => (
                              <CommandItem
                                key={p.id}
                                value={p.nombre}
                                onSelect={() => {
                                  setEntradaForm({
                                    ...entradaForm,
                                    producto_id: p.id.toString(),
                                    costo_unitario: p.precio_costo ? p.precio_costo.toString() : '',
                                    precio_venta: p.precio_venta ? p.precio_venta.toString() : '',
                                    proveedor_id: p.proveedor_id ? p.proveedor_id.toString() : entradaForm.proveedor_id
                                  });
                                  const totalStock = stockTotalMap[p.id] || 0;
                                  setEntradaProductoStock(totalStock);
                                  setEntradaProductoPrecioCosto(p.precio_costo ? parseFloat(p.precio_costo) : 0);
                                  setEntradaCPPAplicado(null);
                                  setEntradaPopoverOpen(false);
                                  setProductoSearchEntrada('');
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    entradaForm.producto_id === p.id.toString() ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                <div className="flex flex-col">
                                  <span>{p.nombre}</span>
                                  {p.codigo_barra && (
                                    <span className="text-xs text-muted-foreground">Código: {p.codigo_barra}</span>
                                  )}
                                </div>
                              </CommandItem>
                            ))}
                        </CommandGroup>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <Label>Almacén</Label>
                  <Select value={entradaForm.almacen_id} onValueChange={(v) => setEntradaForm({...entradaForm, almacen_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar almacén" />
                    </SelectTrigger>
                    <SelectContent>
                      {almacenes.map(a => (
                        <SelectItem key={a.id} value={a.id.toString()}>{a.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Cantidad</Label>
                    <Input
                      type="number"
                      min="1"
                      value={entradaForm.cantidad}
                      onChange={(e) => setEntradaForm({...entradaForm, cantidad: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Precio de Costo (Gs.)</Label>
                    <Input
                      type="number"
                      min="0"
                      placeholder="0"
                      value={entradaForm.costo_unitario}
                      onChange={(e) => { setEntradaForm({...entradaForm, costo_unitario: e.target.value}); setEntradaCPPAplicado(null); }}
                    />
                  </div>
                </div>
                {/* Warning: product already has stock */}
                {entradaForm.producto_id && entradaProductoStock > 0 && (
                  <Alert variant="destructive" className="py-2">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      Este producto tiene <strong>{entradaProductoStock.toLocaleString('es-PY')} unidades</strong> en stock actualmente. ¿Estás seguro de que querés cargar una nueva tanda?
                    </AlertDescription>
                  </Alert>
                )}
                {/* CPP button: shown when existing stock AND qty AND cost are all set */}
                {entradaForm.producto_id && entradaProductoStock > 0 && entradaForm.cantidad && entradaForm.costo_unitario && (
                  (() => {
                    const currentStock = entradaProductoStock;
                    const currentCosto = entradaProductoPrecioCosto;
                    const newQty = parseInt(entradaForm.cantidad) || 0;
                    const newCosto = parseFloat(entradaForm.costo_unitario) || 0;
                    const cpp = newQty + currentStock > 0
                      ? Math.round(((currentStock * currentCosto) + (newQty * newCosto)) / (currentStock + newQty))
                      : newCosto;
                    return (
                      <div className="flex items-center gap-2 bg-muted/40 rounded px-3 py-2">
                        <Calculator className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div className="flex-1 text-xs text-muted-foreground">
                          <span className="font-medium text-foreground">CPP:</span>{' '}
                          ({currentStock} × {currentCosto.toLocaleString('es-PY')} + {newQty} × {newCosto.toLocaleString('es-PY')}) ÷ {currentStock + newQty}{' '}
                          = <span className="font-mono font-semibold text-foreground">Gs. {cpp.toLocaleString('es-PY')}</span>
                        </div>
                        {entradaCPPAplicado === cpp ? (
                          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 font-semibold">
                            ✓ Aplicado
                            <button type="button" className="ml-1 opacity-60 hover:opacity-100" onClick={() => setEntradaCPPAplicado(null)}>✕</button>
                          </span>
                        ) : (
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="text-xs h-7 shrink-0"
                            onClick={() => setEntradaCPPAplicado(cpp)}
                          >
                            Aplicar
                          </Button>
                        )}
                      </div>
                    );
                  })()
                )}
                <div>
                  <Label>Precio de Venta (Gs.) <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
                  <Input
                    type="number"
                    min="0"
                    placeholder="0"
                    value={entradaForm.precio_venta}
                    onChange={(e) => setEntradaForm({...entradaForm, precio_venta: e.target.value})}
                  />
                </div>
                {entradaForm.costo_unitario && entradaForm.cantidad && (
                  <div className="text-sm text-muted-foreground bg-muted/40 rounded px-3 py-2">
                    Total compra: <span className="font-mono font-semibold">
                      Gs. {(parseFloat(entradaForm.costo_unitario || 0) * parseInt(entradaForm.cantidad || 0)).toLocaleString('es-PY')}
                    </span>
                  </div>
                )}
                <div>
                  <Label>Proveedor</Label>
                  <Select value={entradaForm.proveedor_id} onValueChange={(v) => setEntradaForm({...entradaForm, proveedor_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar proveedor (opcional)" />
                    </SelectTrigger>
                    <SelectContent>
                      {proveedores.map(p => (
                        <SelectItem key={p.id} value={p.id.toString()}>{p.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Condición de Pago</Label>
                  <div className="flex gap-2 mt-1">
                    <Button
                      type="button"
                      variant={entradaForm.condicion_pago === 'contado' ? 'default' : 'outline'}
                      className="flex-1 gap-2"
                      onClick={() => setEntradaForm({...entradaForm, condicion_pago: 'contado', fecha_limite_pago: ''})}
                    >
                      <ShoppingCart className="h-4 w-4" />
                      Contado
                    </Button>
                    <Button
                      type="button"
                      variant={entradaForm.condicion_pago === 'credito' ? 'default' : 'outline'}
                      className="flex-1 gap-2"
                      onClick={() => setEntradaForm({...entradaForm, condicion_pago: 'credito'})}
                    >
                      <CreditCard className="h-4 w-4" />
                      Crédito
                    </Button>
                  </div>
                </div>
                {entradaForm.condicion_pago === 'credito' && (
                  <div>
                    <Label>Fecha Límite de Pago</Label>
                    <DatePickerInput
                      value={entradaForm.fecha_limite_pago}
                      onChange={(val) => setEntradaForm({...entradaForm, fecha_limite_pago: val})}
                    />
                  </div>
                )}
                <div>
                  <Label>Notas (opcional)</Label>
                  <Input
                    placeholder="Ej: Factura #1234, lote especial..."
                    value={entradaForm.notas}
                    onChange={(e) => setEntradaForm({...entradaForm, notas: e.target.value})}
                  />
                </div>
                <Button type="submit" className="w-full">Registrar Entrada</Button>
              </form>
            </DialogContent>
          </Dialog>
          )}

          {/* Salida Stock */}
          {userPermisos.includes('stock.salida') && (
            <Dialog open={salidaDialogOpen} onOpenChange={setSalidaDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive" data-testid="salida-stock-btn">
                  <Minus className="mr-2 h-4 w-4" />
                  Salida
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogDescription className="hidden">Formulario para registrar una salida o eliminación de stock</DialogDescription>
              <DialogHeader>
                <DialogTitle>Salida/Eliminación de Stock</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSalida} className="space-y-4">
                <div>
                  <Label>Producto</Label>
                  <Popover open={salidaPopoverOpen} onOpenChange={setSalidaPopoverOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={salidaPopoverOpen}
                        className="w-full justify-between"
                      >
                        {salidaForm.producto_id
                          ? productos.find((p) => p.id.toString() === salidaForm.producto_id)?.nombre
                          : "Buscar producto..."}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[400px] p-0">
                      <Command shouldFilter={false}>
                        <CommandInput 
                          placeholder="Buscar por nombre o código..." 
                          value={productoSearchSalida}
                          onValueChange={setProductoSearchSalida}
                        />
                        <CommandEmpty>No se encontró el producto.</CommandEmpty>
                        <CommandGroup className="max-h-64 overflow-auto">
                          {productos
                            .filter(p => 
                              !productoSearchSalida || 
                              p.nombre.toLowerCase().includes(productoSearchSalida.toLowerCase()) ||
                              p.codigo_barra?.toLowerCase().includes(productoSearchSalida.toLowerCase())
                            )
                            .map((p) => (
                              <CommandItem
                                key={p.id}
                                value={p.nombre}
                                onSelect={() => {
                                  setSalidaForm({...salidaForm, producto_id: p.id.toString()});
                                  setSalidaPopoverOpen(false);
                                  setProductoSearchSalida('');
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    salidaForm.producto_id === p.id.toString() ? "opacity-100" : "opacity-0"
                                  )}
                                />
                                <div className="flex flex-col">
                                  <span>{p.nombre}</span>
                                  {p.codigo_barra && (
                                    <span className="text-xs text-muted-foreground">Código: {p.codigo_barra}</span>
                                  )}
                                </div>
                              </CommandItem>
                            ))}
                        </CommandGroup>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <Label>Almacén</Label>
                  <Select value={salidaForm.almacen_id} onValueChange={(v) => setSalidaForm({...salidaForm, almacen_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar almacén" />
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
                    value={salidaForm.cantidad}
                    onChange={(e) => setSalidaForm({...salidaForm, cantidad: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Motivo</Label>
                  <Input
                    value={salidaForm.motivo}
                    onChange={(e) => setSalidaForm({...salidaForm, motivo: e.target.value})}
                    placeholder="Ej: Producto dañado, vencido, etc."
                  />
                </div>
                <Button type="submit" variant="destructive" className="w-full">Registrar Salida</Button>
              </form>
            </DialogContent>
          </Dialog>
          )}
        </div>
      </div>

      {/* Almacenes Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {almacenes.map((almacen) => {
          const stockAlmacen = stock.filter(s => s.almacen_id === almacen.id);
          const totalItems = stockAlmacen.reduce((sum, s) => sum + s.cantidad, 0);
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
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Inventario {selectedAlmacen && `- ${almacenes.find(a => a.id.toString() === selectedAlmacen)?.nombre}`}
            </CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar producto..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredStock.length === 0 ? (
            <div className="text-center py-12">
              <Package className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No hay stock registrado</p>
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
        </CardContent>
      </Card>
      {/* Historial Dialog */}
      <Dialog open={historialDialogOpen} onOpenChange={(open) => { setHistorialDialogOpen(open); if (!open) setHistorialFilter('ALL'); }}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogDescription className="hidden">Historial de movimientos del producto</DialogDescription>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5" />
              Historial &mdash; {historialProducto?.nombre}
            </DialogTitle>
          </DialogHeader>
          {/* Filter buttons */}
          {!historialLoading && historialData.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {[
                { key: 'ALL', label: 'Todos' },
                { key: 'ENTRADA', label: 'Entradas' },
                { key: 'VENTA', label: 'Ventas' },
                { key: 'BAJA', label: 'Bajas' },
              ].map(f => (
                <Button
                  key={f.key}
                  type="button"
                  size="sm"
                  variant={historialFilter === f.key ? 'default' : 'outline'}
                  className="h-7 text-xs"
                  onClick={() => setHistorialFilter(f.key)}
                >
                  {f.label}
                </Button>
              ))}
            </div>
          )}
          {historialLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : historialData.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <History className="h-10 w-10 mx-auto mb-3 opacity-40" />
              No hay movimientos registrados para este producto.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Almacén</TableHead>
                  <TableHead className="text-right">Cantidad</TableHead>
                  <TableHead className="text-right">Costo Real</TableHead>
                  <TableHead className="text-right">CPP Pond.</TableHead>
                  <TableHead className="text-right">Total Compra</TableHead>
                  <TableHead>Condición</TableHead>
                  <TableHead>Proveedor</TableHead>
                  <TableHead>Notas</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historialData
                  .filter(mov => {
                    if (historialFilter === 'ALL') return true;
                    if (historialFilter === 'ENTRADA') return mov.tipo === 'ENTRADA';
                    if (historialFilter === 'VENTA') return mov.tipo === 'VENTA' || (mov.tipo === 'SALIDA' && mov.referencia_tipo === 'venta');
                    if (historialFilter === 'BAJA') return mov.tipo === 'SALIDA' && mov.referencia_tipo !== 'venta';
                    if (historialFilter === 'TRASPASO') return mov.tipo === 'TRASPASO';
                    return true;
                  })
                  .map((mov) => {
                  const esVenta = mov.tipo === 'VENTA' || (mov.tipo === 'SALIDA' && mov.referencia_tipo === 'venta');
                  const esBaja = mov.tipo === 'SALIDA' && mov.referencia_tipo !== 'venta';
                  const tipoColorResolved = esVenta
                    ? 'text-amber-500 dark:text-amber-400'
                    : esBaja
                    ? 'text-red-600 dark:text-red-400'
                    : mov.tipo === 'ENTRADA'
                    ? 'text-green-600 dark:text-green-400'
                    : mov.tipo === 'TRASPASO'
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-muted-foreground';
                  const tipoLabelResolved = esVenta ? 'Venta'
                    : esBaja ? 'Baja'
                    : mov.tipo === 'ENTRADA' ? 'Entrada'
                    : mov.tipo === 'TRASPASO' ? 'Traspaso'
                    : mov.tipo;
                  return (
                    <TableRow key={mov.id}>
                      <TableCell className="text-xs whitespace-nowrap">
                        {mov.creado_en ? new Date(mov.creado_en).toLocaleDateString('es-PY', {
                          day: '2-digit', month: '2-digit', year: 'numeric',
                          hour: '2-digit', minute: '2-digit'
                        }) : '-'}
                      </TableCell>
                      <TableCell className={cn('font-semibold text-xs', tipoColorResolved)}>
                        {tipoLabelResolved}
                      </TableCell>
                      <TableCell>
                        {mov.tipo === 'ENTRADA' && mov.estado ? (
                          <Badge
                            className={cn('text-xs', mov.estado === 'Activo'
                              ? 'badge-success'
                              : 'bg-muted text-muted-foreground'
                            )}
                          >
                            {mov.estado}
                          </Badge>
                        ) : '-'}
                      </TableCell>
                      <TableCell className="text-xs">{mov.almacen_nombre || '-'}</TableCell>
                      <TableCell className="text-right font-mono font-bold">
                        {mov.cantidad > 0 ? `+${mov.cantidad}` : mov.cantidad}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {mov.costo_unitario != null ? formatCurrency(mov.costo_unitario) : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {mov.tipo === 'ENTRADA' && mov.costo_ponderado != null
                          ? <span className="text-amber-500 dark:text-amber-400">{formatCurrency(mov.costo_ponderado)}</span>
                          : <span className="text-muted-foreground">-</span>}
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
