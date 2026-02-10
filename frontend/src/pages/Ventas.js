import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { 
  Search, Plus, Trash2, ShoppingCart, User, Barcode, 
  CreditCard, Truck, Store, Loader2, Check, X, Package
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import PrintModal from '../components/PrintModal';

const Ventas = () => {
  const { api, empresa, user, hasPermission } = useApp();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Editing existing sale
  const editVentaId = searchParams.get('edit');
  const [editingVenta, setEditingVenta] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  
  // State
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [vehiculos, setVehiculos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [representante, setRepresentante] = useState(null);
  const [isRepresentante, setIsRepresentante] = useState(false);
  const [cart, setCart] = useState([]);
  const [tipoPago, setTipoPago] = useState('EFECTIVO');
  const [crearPendiente, setCrearPendiente] = useState(false);
  const [esDelivery, setEsDelivery] = useState(false);
  const [vehiculoId, setVehiculoId] = useState('');
  const [responsableId, setResponsableId] = useState('');
  
  const [searchCliente, setSearchCliente] = useState('');
  const [searchProducto, setSearchProducto] = useState('');
  const [barcodeInput, setBarcodeInput] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [clienteDialogOpen, setClienteDialogOpen] = useState(false);
  
  // Print modal state
  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [lastVentaId, setLastVentaId] = useState(null);
  
  // Cash payment modal state
  const [cashModalOpen, setCashModalOpen] = useState(false);
  const [montoPagado, setMontoPagado] = useState('');
  const [vuelto, setVuelto] = useState(0);
  
  // Load data
  useEffect(() => {
    const fetchData = async () => {
      if (!empresa?.id) return;
      
      try {
        const [clientesData, productosData, materiasData, vehiculosData, usuariosData] = await Promise.all([
          api(`/clientes?empresa_id=${empresa.id}`),
          api(`/productos?empresa_id=${empresa.id}`),
          api(`/materias-laboratorio/disponibles?empresa_id=${empresa.id}`),
          api(`/vehiculos?empresa_id=${empresa.id}`),
          api(`/usuarios?empresa_id=${empresa.id}`)
        ]);
        
        setClientes(clientesData);
        setProductos(productosData);
        setMaterias(materiasData);
        setVehiculos(vehiculosData);
        setUsuarios(usuariosData);
      } catch (e) {
        console.error('Error loading data:', e);
        toast.error('Error al cargar datos');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [empresa?.id, api]);

  // Load existing sale if editing
  useEffect(() => {
    const loadEditVenta = async () => {
      if (!editVentaId || !empresa?.id) return;
      
      try {
        const venta = await api(`/ventas/${editVentaId}`);
        
        if (venta.estado !== 'PENDIENTE') {
          toast.error('Solo se pueden editar ventas PENDIENTES');
          navigate('/ventas');
          return;
        }
        
        setEditingVenta(venta);
        setIsEditMode(true);
        
        // Load cliente
        const cliente = clientes.find(c => c.id === venta.cliente_id);
        if (cliente) setSelectedCliente(cliente);
        
        // Load representante if exists
        if (venta.representante_cliente_id) {
          const rep = clientes.find(c => c.id === venta.representante_cliente_id);
          if (rep) {
            setRepresentante(rep);
            setIsRepresentante(true);
          }
        }
        
        // Load cart items
        const cartItems = venta.items.map(item => ({
          producto_id: item.producto_id || null,
          materia_laboratorio_id: item.materia_laboratorio_id || null,
          nombre: item.producto_nombre || item.materia_nombre || 'Producto',
          cantidad: item.cantidad,
          precio_unitario: parseFloat(item.precio_unitario),
          observaciones: item.observaciones || ''
        }));
        setCart(cartItems);
        
        // Load other fields
        setTipoPago(venta.tipo_pago || 'EFECTIVO');
        setEsDelivery(venta.es_delivery || false);
        
        toast.info('Venta pendiente cargada - Puede editarla');
      } catch (e) {
        console.error('Error loading venta:', e);
        toast.error('Error al cargar la venta');
        navigate('/ventas');
      }
    };
    
    if (clientes.length > 0) {
      loadEditVenta();
    }
  }, [editVentaId, empresa?.id, api, clientes, navigate]);

  // Barcode scanner handler
  const handleBarcodeSearch = useCallback(async (code) => {
    if (!code.trim()) return;
    
    if (!selectedCliente) {
      toast.error('Primero seleccione un cliente');
      return;
    }
    
    try {
      // Try product first
      const product = productos.find(p => p.codigo_barra === code);
      if (product) {
        addToCart(product, 'producto');
        setBarcodeInput('');
        return;
      }
      
      // Try materia
      const materia = materias.find(m => m.codigo_barra === code);
      if (materia) {
        addToCart(materia, 'materia');
        setBarcodeInput('');
        return;
      }
      
      toast.error('Producto no encontrado');
    } catch (e) {
      toast.error('Error al buscar producto');
    }
  }, [productos, materias, selectedCliente]);

  // Handle barcode input (USB scanner sends Enter key)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && barcodeInput) {
        handleBarcodeSearch(barcodeInput);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [barcodeInput, handleBarcodeSearch]);

  const addToCart = (item, type) => {
    if (!selectedCliente) {
      toast.error('Primero seleccione un cliente');
      return;
    }
    
    const existingIndex = cart.findIndex(c => 
      type === 'producto' ? c.producto_id === item.id : c.materia_laboratorio_id === item.id
    );
    
    if (type === 'materia') {
      // Materias can only be added once
      if (existingIndex >= 0) {
        toast.error('Esta materia ya está en el carrito');
        return;
      }
      
      // Check max items limit (10 items para no desbordar boleta)
      if (cart.length >= 10) {
        toast.error('Máximo 10 productos por venta. Cree una nueva venta para más items.');
        return;
      }
      
      setCart([...cart, {
        materia_laboratorio_id: item.id,
        nombre: item.nombre,
        cantidad: 1,
        precio_unitario: parseFloat(item.precio),
        observaciones: ''
      }]);
      
      // Warning when approaching limit
      if (cart.length >= 7) {
        toast.warning(`⚠️ ${cart.length + 1}/10 productos. La boleta tiene espacio limitado.`);
      }
    } else {
      // Products can be added multiple times
      if (existingIndex >= 0) {
        const newCart = [...cart];
        const newQty = newCart[existingIndex].cantidad + 1;
        
        // Check stock
        if (newQty > item.stock_total) {
          toast.error(`Stock insuficiente. Disponible: ${item.stock_total}`);
          return;
        }
        
        newCart[existingIndex].cantidad = newQty;
        setCart(newCart);
      } else {
        if (item.stock_total < 1) {
          toast.error('Producto sin stock');
          return;
        }
        
        // Check max items limit (10 items para no desbordar boleta)
        if (cart.length >= 10) {
          toast.error('Máximo 10 productos por venta. Cree una nueva venta para más items.');
          return;
        }
        
        setCart([...cart, {
          producto_id: item.id,
          nombre: item.nombre,
          cantidad: 1,
          precio_unitario: parseFloat(item.precio_venta),
          stock_disponible: item.stock_total,
          observaciones: ''
        }]);
        
        // Warning when approaching limit
        if (cart.length >= 7) {
          toast.warning(`⚠️ ${cart.length + 1}/10 productos. La boleta tiene espacio limitado.`);
        }
      }
    }
    
    toast.success(`${item.nombre} agregado al carrito`);
  };

  const updateCartItem = (index, field, value) => {
    const newCart = [...cart];
    
    if (field === 'cantidad') {
      const item = newCart[index];
      if (item.producto_id && value > item.stock_disponible) {
        toast.error(`Stock máximo: ${item.stock_disponible}`);
        return;
      }
      if (value < 1) return;
    }
    
    // Validar permiso para modificar precio
    if (field === 'precio_unitario') {
      if (!hasPermission('ventas.modificar_precio')) {
        toast.error('No tiene permiso para modificar precios');
        return;
      }
      if (value < 0) return;
    }
    
    newCart[index][field] = value;
    setCart(newCart);
  };

  const removeFromCart = (index) => {
    setCart(cart.filter((_, i) => i !== index));
  };

  // Calculate totals - usar privilegios del representante si existe
  const clientePrivilegios = isRepresentante && representante ? representante : selectedCliente;
  const subtotal = cart.reduce((sum, item) => sum + (item.cantidad * item.precio_unitario), 0);
  
  // Aplicar descuento solo si el usuario tiene el permiso
  const descuentoPorcentaje = (hasPermission('ventas.aplicar_descuento') && clientePrivilegios?.descuento_porcentaje) || 0;
  const descuento = subtotal * descuentoPorcentaje / 100;
  const subtotalConDescuento = subtotal - descuento;
  const iva = subtotalConDescuento * 10 / 110; // IVA 10% included
  const total = subtotalConDescuento;

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PY', {
      style: 'currency',
      currency: 'PYG',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  // Calculate change when cash amount changes
  useEffect(() => {
    if (montoPagado && !isNaN(montoPagado)) {
      const cambio = parseFloat(montoPagado) - total;
      setVuelto(cambio > 0 ? cambio : 0);
    } else {
      setVuelto(0);
    }
  }, [montoPagado, total]);

  const handleConfirmarVentaClick = () => {
    if (!selectedCliente) {
      toast.error('Seleccione un cliente');
      return;
    }
    
    if (cart.length === 0) {
      toast.error('Agregue productos al carrito');
      return;
    }
    
    // Validate cheque payment
    if (tipoPago === 'CHEQUE' && !selectedCliente.acepta_cheque) {
      toast.error('Este cliente no tiene habilitado el pago con cheque');
      return;
    }
    
    // If cash payment, open cash modal
    if (tipoPago === 'EFECTIVO') {
      setMontoPagado('');
      setVuelto(0);
      setCashModalOpen(true);
    } else {
      // For other payment types, proceed directly
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    if (!selectedCliente) {
      toast.error('Seleccione un cliente');
      return;
    }
    
    if (cart.length === 0) {
      toast.error('Agregue productos al carrito');
      return;
    }
    
    setSubmitting(true);
    setCashModalOpen(false);
    
    try {
      // Caso 1: EDITAR venta pendiente existente
      if (isEditMode && editingVenta) {
        const updateData = {
          cliente_id: selectedCliente.id,
          representante_cliente_id: isRepresentante ? representante?.id : null,
          tipo_pago: tipoPago,
          es_delivery: esDelivery,
          items: cart.map(item => ({
            producto_id: item.producto_id || null,
            materia_laboratorio_id: item.materia_laboratorio_id || null,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            observaciones: item.observaciones || null
          }))
        };
        
        // Update the sale
        await api(`/ventas/${editingVenta.id}`, {
          method: 'PUT',
          body: JSON.stringify(updateData)
        });
        
        // Ask if user wants to confirm the sale now
        if (window.confirm('¿Desea confirmar esta venta ahora? (Se validará stock y crédito)')) {
          await api(`/ventas/${editingVenta.id}/confirmar-pendiente`, { method: 'POST' });
          toast.success('Venta actualizada y confirmada');
        } else {
          toast.success('Venta actualizada - Sigue pendiente');
        }
        
        // Redirect to historial
        navigate('/historial-ventas');
        return;
      }
      
      // Caso 2: CREAR nueva venta
      const ventaData = {
        empresa_id: empresa.id,
        cliente_id: selectedCliente.id,
        representante_cliente_id: isRepresentante ? representante?.id : null,
        usuario_id: user.id,
        es_delivery: esDelivery,
        tipo_pago: tipoPago,
        items: cart.map(item => ({
          producto_id: item.producto_id || null,
          materia_laboratorio_id: item.materia_laboratorio_id || null,
          cantidad: item.cantidad,
          precio_unitario: item.precio_unitario,
          observaciones: item.observaciones || null
        }))
      };
      
      // Si crear como pendiente
      if (crearPendiente) {
        const venta = await api('/ventas?crear_pendiente=true', {
          method: 'POST',
          body: JSON.stringify(ventaData)
        });
        
        toast.success('Venta creada como PENDIENTE - Puede confirmarla desde Historial de Ventas');
        
        // Store venta ID for printing and show print modal
        setLastVentaId(venta.id);
        setPrintModalOpen(true);
      } else {
        // Flujo normal: crear y confirmar
        const venta = await api('/ventas', {
          method: 'POST',
          body: JSON.stringify(ventaData)
        });
        
        // Confirm sale (this creates the delivery entry if es_delivery=true)
        await api(`/ventas/${venta.id}/confirmar`, { method: 'POST' });
        
        toast.success(esDelivery ? 'Venta creada - Asigne delivery desde el módulo Delivery' : 'Venta creada exitosamente');
        
        // Store venta ID for printing and show print modal
        setLastVentaId(venta.id);
        setPrintModalOpen(true);
      }
      
      // Reset form
      setSelectedCliente(null);
      setRepresentante(null);
      setIsRepresentante(false);
      setCart([]);
      setTipoPago('EFECTIVO');
      setCrearPendiente(false);
      setEsDelivery(false);
      setVehiculoId('');
      setResponsableId('');
      
      // Reload materias
      const newMaterias = await api(`/materias-laboratorio/disponibles?empresa_id=${empresa.id}`);
      setMaterias(newMaterias);
      
    } catch (e) {
      toast.error(e.message || 'Error al procesar venta');
    } finally {
      setSubmitting(false);
    }
  };

  // Filter products
  const filteredProductos = productos.filter(p => 
    p.nombre.toLowerCase().includes(searchProducto.toLowerCase()) ||
    p.codigo_barra?.toLowerCase().includes(searchProducto.toLowerCase()) ||
    p.id.toString() === searchProducto
  );

  // Filter clients
  const filteredClientes = clientes.filter(c =>
    c.nombre.toLowerCase().includes(searchCliente.toLowerCase()) ||
    c.ruc?.toLowerCase().includes(searchCliente.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" data-testid="ventas-page">
      {/* Products Section - Left/Main */}
      <div className="lg:col-span-2 space-y-4">
        {/* Client Selection */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Cliente
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedCliente ? (
              <div className="flex items-center justify-between p-3 bg-secondary rounded-lg">
                <div>
                  <p className="font-medium">{selectedCliente.nombre} {selectedCliente.apellido}</p>
                  <p className="text-sm text-muted-foreground">
                    RUC: {selectedCliente.ruc || 'N/A'} | Tel: {selectedCliente.telefono || 'N/A'}
                  </p>
                  {selectedCliente.descuento_porcentaje > 0 && (
                    <Badge className={cn(
                      "mt-1",
                      hasPermission('ventas.aplicar_descuento') ? "badge-success" : "badge-muted"
                    )}>
                      {selectedCliente.descuento_porcentaje}% descuento
                      {!hasPermission('ventas.aplicar_descuento') && " (sin permiso)"}
                    </Badge>
                  )}
                </div>
                <Button variant="ghost" size="icon" onClick={() => setSelectedCliente(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Dialog open={clienteDialogOpen} onOpenChange={setClienteDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="w-full" data-testid="select-cliente-btn">
                    <User className="mr-2 h-4 w-4" />
                    Seleccionar Cliente
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-lg">
                  <DialogHeader>
                    <DialogTitle>Seleccionar Cliente</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Buscar por nombre o RUC..."
                        className="pl-9"
                        value={searchCliente}
                        onChange={(e) => setSearchCliente(e.target.value)}
                        data-testid="search-cliente"
                      />
                    </div>
                    <ScrollArea className="h-64">
                      <div className="space-y-2">
                        {filteredClientes.map((cliente) => (
                          <div
                            key={cliente.id}
                            className="p-3 rounded-lg border hover:bg-secondary cursor-pointer transition-colors"
                            onClick={() => {
                              setSelectedCliente(cliente);
                              setClienteDialogOpen(false);
                            }}
                            data-testid={`cliente-option-${cliente.id}`}
                          >
                            <p className="font-medium">{cliente.nombre} {cliente.apellido}</p>
                            <p className="text-sm text-muted-foreground">
                              RUC: {cliente.ruc || 'N/A'}
                            </p>
                          </div>
                        ))}
                        {filteredClientes.length === 0 && (
                          <div className="text-center py-8">
                            <p className="text-muted-foreground mb-4">No se encontraron clientes</p>
                            <Button onClick={() => navigate('/clientes')}>
                              <Plus className="mr-2 h-4 w-4" />
                              Crear Cliente
                            </Button>
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                </DialogContent>
              </Dialog>
            )}

            {/* Representante checkbox */}
            {selectedCliente && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="representante"
                    checked={isRepresentante}
                    onCheckedChange={setIsRepresentante}
                  />
                  <Label htmlFor="representante">Representa a otro cliente</Label>
                </div>
                
                {isRepresentante && (
                  <Select 
                    value={representante?.id?.toString() || ''} 
                    onValueChange={(val) => setRepresentante(clientes.find(c => c.id === parseInt(val)))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar cliente representado" />
                    </SelectTrigger>
                    <SelectContent>
                      {clientes.filter(c => c.id !== selectedCliente.id).map((c) => (
                        <SelectItem key={c.id} value={c.id.toString()}>
                          {c.nombre} {c.apellido}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Barcode Scanner */}
        <Card>
          <CardContent className="p-4">
            <div className="relative">
              <Barcode className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Escanear código de barras..."
                className="pl-9 font-mono"
                value={barcodeInput}
                onChange={(e) => setBarcodeInput(e.target.value)}
                data-testid="barcode-input"
              />
            </div>
          </CardContent>
        </Card>

        {/* Products Grid */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle>Productos</CardTitle>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nombre o ID..."
                  className="pl-9"
                  value={searchProducto}
                  onChange={(e) => setSearchProducto(e.target.value)}
                  data-testid="search-producto"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96">
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {filteredProductos.map((producto) => (
                  <div
                    key={producto.id}
                    className={cn(
                      "p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md",
                      producto.stock_total < 1 && "opacity-50 cursor-not-allowed"
                    )}
                    onClick={() => producto.stock_total > 0 && addToCart(producto, 'producto')}
                    data-testid={`producto-card-${producto.id}`}
                  >
                    {producto.imagen_url ? (
                      <img 
                        src={producto.imagen_url} 
                        alt={producto.nombre}
                        className="w-full h-20 object-cover rounded mb-2"
                      />
                    ) : (
                      <div className="w-full h-20 bg-muted rounded mb-2 flex items-center justify-center">
                        <Package className="h-8 w-8 text-muted-foreground" />
                      </div>
                    )}
                    <Badge variant="outline" className="mb-1 text-xs">ID: {producto.id}</Badge>
                    <p className="font-medium text-sm truncate">{producto.nombre}</p>
                    <p className="font-mono-data text-sm text-primary font-semibold">
                      {formatCurrency(producto.precio_venta)}
                    </p>
                    <Badge variant={producto.stock_total > 0 ? "secondary" : "destructive"} className="mt-1">
                      Stock: {producto.stock_total}
                    </Badge>
                  </div>
                ))}
              </div>
            </ScrollArea>

            {/* Materias Laboratorio Section */}
            {materias.length > 0 && (
              <>
                <Separator className="my-4" />
                <div>
                  <h4 className="font-semibold mb-3">Materias de Laboratorio</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {materias.map((materia) => (
                      <div
                        key={materia.id}
                        className="p-3 rounded-lg border border-dashed cursor-pointer hover:bg-secondary transition-colors"
                        onClick={() => addToCart(materia, 'materia')}
                        data-testid={`materia-card-${materia.id}`}
                      >
                        <p className="font-medium text-sm">{materia.nombre}</p>
                        <p className="text-xs text-muted-foreground truncate">{materia.descripcion}</p>
                        <p className="font-mono-data text-sm text-primary font-semibold mt-1">
                          {formatCurrency(materia.precio)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cart Section - Right */}
      <div className="space-y-4">
        <Card className="sticky top-20">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5" />
              Carrito
              {cart.length > 0 && (
                <Badge 
                  className="ml-auto" 
                  variant={cart.length >= 8 ? "destructive" : cart.length >= 6 ? "warning" : "default"}
                >
                  {cart.length}/10
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {cart.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                El carrito está vacío
              </p>
            ) : (
              <ScrollArea className="h-64">
                <div className="space-y-3">
                  {cart.map((item, idx) => (
                    <div key={idx} className="p-3 bg-secondary rounded-lg">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-medium text-sm">{item.nombre}</p>
                          <p className="font-mono-data text-xs text-muted-foreground">
                            {formatCurrency(item.precio_unitario)} x {item.cantidad}
                          </p>
                        </div>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-6 w-6"
                          onClick={() => removeFromCart(idx)}
                        >
                          <Trash2 className="h-3 w-3 text-destructive" />
                        </Button>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => updateCartItem(idx, 'cantidad', item.cantidad - 1)}
                          disabled={item.materia_laboratorio_id}
                        >
                          -
                        </Button>
                        <Input
                          type="number"
                          value={item.cantidad}
                          onChange={(e) => updateCartItem(idx, 'cantidad', parseInt(e.target.value) || 1)}
                          className="w-14 h-7 text-center"
                          disabled={item.materia_laboratorio_id}
                        />
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => updateCartItem(idx, 'cantidad', item.cantidad + 1)}
                          disabled={item.materia_laboratorio_id}
                        >
                          +
                        </Button>
                      </div>
                      {/* Precio editable */}
                      <div className="flex items-center gap-2 mt-2">
                        <Label className="text-xs">Precio:</Label>
                        <Input
                          type="number"
                          value={item.precio_unitario}
                          onChange={(e) => updateCartItem(idx, 'precio_unitario', parseFloat(e.target.value) || 0)}
                          className="w-28 h-7 text-right font-mono-data"
                          disabled={!hasPermission('ventas.modificar_precio')}
                        />
                        <span className="text-sm font-mono-data font-semibold ml-auto">
                          = {formatCurrency(item.cantidad * item.precio_unitario)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            <Separator />

            {/* Totals */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span className="font-mono-data">{formatCurrency(subtotal)}</span>
              </div>
              {descuento > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Descuento ({descuentoPorcentaje}%)</span>
                  <span className="font-mono-data">-{formatCurrency(descuento)}</span>
                </div>
              )}
              <div className="flex justify-between text-muted-foreground">
                <span>IVA 10% (incluido)</span>
                <span className="font-mono-data">{formatCurrency(iva)}</span>
              </div>
              <Separator />
              <div className="flex justify-between text-lg font-bold">
                <span>Total</span>
                <span className="font-mono-data text-primary">{formatCurrency(total)}</span>
              </div>
            </div>

            <Separator />

            {/* Payment Options */}
            <div className="space-y-3">
              <div>
                <Label>Tipo de Pago</Label>
                <Select value={tipoPago} onValueChange={setTipoPago}>
                  <SelectTrigger data-testid="tipo-pago-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EFECTIVO">Efectivo</SelectItem>
                    <SelectItem value="TARJETA">Tarjeta</SelectItem>
                    <SelectItem value="TRANSFERENCIA">Transferencia</SelectItem>
                    <SelectItem 
                      value="CHEQUE" 
                      disabled={selectedCliente && !selectedCliente.acepta_cheque}
                    >
                      Cheque {selectedCliente && !selectedCliente.acepta_cheque && '(No habilitado)'}
                    </SelectItem>
                    <SelectItem value="CREDITO">Crédito</SelectItem>
                  </SelectContent>
                </Select>
                {tipoPago === 'CHEQUE' && selectedCliente && !selectedCliente.acepta_cheque && (
                  <p className="text-xs text-destructive mt-1">
                    Este cliente no tiene habilitado el pago con cheque
                  </p>
                )}
              </div>

              {/* Crear como Pendiente Option - Solo visible en modo creación */}
              {!isEditMode && (
                <div className="flex items-center space-x-2 bg-yellow-50 dark:bg-yellow-950/30 p-2 rounded border border-yellow-200 dark:border-yellow-800">
                  <Checkbox
                    id="crearPendiente"
                    checked={crearPendiente}
                    onCheckedChange={setCrearPendiente}
                  />
                  <Label htmlFor="crearPendiente" className="text-sm text-yellow-900 dark:text-yellow-100">
                    Crear como venta pendiente (sin confirmar pago)
                  </Label>
                </div>
              )}

              {/* Delivery Option */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="esDelivery"
                  checked={esDelivery}
                  onCheckedChange={setEsDelivery}
                />
                <Label htmlFor="esDelivery" className="flex items-center gap-2">
                  <Truck className="h-4 w-4" />
                  Es Delivery
                </Label>
              </div>

              {esDelivery && (
                <div className="p-3 bg-secondary rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    ℹ️ La asignación de vehículo y responsable se realiza desde el módulo <strong>Delivery</strong>
                  </p>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button 
              className="w-full" 
              size="lg"
              disabled={!selectedCliente || cart.length === 0 || submitting}
              onClick={handleConfirmarVentaClick}
              data-testid="confirmar-venta-btn"
            >
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Check className="mr-2 h-4 w-4" />
                  {isEditMode ? 'Actualizar Venta Pendiente' : 'Confirmar Venta'}
                </>
              )}
            </Button>
            
            {isEditMode && (
              <p className="text-xs text-muted-foreground text-center mt-2">
                Al actualizar, se preguntará si desea confirmar el pago
              </p>
            )}
          </CardContent>
        </Card>
      </div>
      
      {/* Cash Payment Modal */}
      <Dialog open={cashModalOpen} onOpenChange={setCashModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Pago en Efectivo
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-6">
            {/* Total to Pay */}
            <div className="p-4 bg-primary/10 rounded-lg border-2 border-primary/20">
              <p className="text-sm text-muted-foreground mb-1">Total a Pagar</p>
              <p className="text-3xl font-bold font-mono-data text-primary">
                {formatCurrency(total)}
              </p>
            </div>

            {/* Amount Paid Input */}
            <div className="space-y-2">
              <Label htmlFor="montoPagado">Monto que Paga el Cliente</Label>
              <Input
                id="montoPagado"
                type="number"
                placeholder="Ej: 200000"
                value={montoPagado}
                onChange={(e) => setMontoPagado(e.target.value)}
                className="text-lg font-mono-data text-right"
                autoFocus
              />
            </div>

            {/* Change Display */}
            {montoPagado && parseFloat(montoPagado) >= total && (
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border-2 border-green-500/30">
                <p className="text-sm text-muted-foreground mb-1">Vuelto</p>
                <p className="text-3xl font-bold font-mono-data text-green-600 dark:text-green-400">
                  {formatCurrency(vuelto)}
                </p>
              </div>
            )}

            {/* Warning if insufficient */}
            {montoPagado && parseFloat(montoPagado) < total && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-300 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400">
                  ⚠️ El monto es insuficiente. Falta: {formatCurrency(total - parseFloat(montoPagado))}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setCashModalOpen(false)}
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!montoPagado || parseFloat(montoPagado) < total || submitting}
                className="flex-1"
              >
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Procesando...
                  </>
                ) : (
                  <>
                    <Check className="mr-2 h-4 w-4" />
                    Aceptar Venta
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Print Modal */}
      <PrintModal 
        open={printModalOpen} 
        onOpenChange={setPrintModalOpen}
        ventaId={lastVentaId}
      />
    </div>
  );
};

export default Ventas;
