import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from './ui/command';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { ChevronsUpDown, Check, ShoppingCart, CreditCard, AlertTriangle, Calculator } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import { DatePickerInput } from './ui/date-picker-input';
import { Alert, AlertDescription } from './ui/alert';

const ALMACEN_DEFAULT_NOMBRE = 'Tienda';

const emptyForm = {
  producto_id: '',
  cantidad: '',
  proveedor_id: '',
  costo_unitario: '',
  precio_venta: '',
  condicion_pago: 'contado',
  fecha_limite_pago: '',
  notas: ''
};

// Dialog de entrada de stock reutilizable desde Stock.js y Productos.js.
// El almacén se resuelve automáticamente a "Tienda" (único almacén operativo)
// y nunca se muestra al usuario.
const EntradaStockDialog = ({ open, onOpenChange, productoIdInicial, onSuccess }) => {
  const { api, empresa } = useApp();
  const [productos, setProductos] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [almacenId, setAlmacenId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [productoSearch, setProductoSearch] = useState('');
  // CPP aplicado al precio de costo del producto (distinto del costo real de compra)
  const [cppAplicado, setCppAplicado] = useState(null);

  useEffect(() => {
    if (!open || !empresa?.id) return;
    (async () => {
      try {
        const [productosData, proveedoresData, almacenesData] = await Promise.all([
          api(`/productos?empresa_id=${empresa.id}`),
          api(`/proveedores?empresa_id=${empresa.id}`),
          api(`/almacenes?empresa_id=${empresa.id}`)
        ]);
        setProductos(productosData);
        setProveedores(proveedoresData);
        const tienda = almacenesData.find(a => a.nombre === ALMACEN_DEFAULT_NOMBRE && a.estado !== false);
        const activo = tienda || almacenesData.find(a => a.estado !== false) || almacenesData[0];
        setAlmacenId(activo?.id || null);
      } catch (e) {
        toast.error('Error al cargar datos');
      }
    })();
  }, [open, empresa?.id]);

  useEffect(() => {
    if (open && productoIdInicial) {
      const producto = productos.find(p => p.id === productoIdInicial);
      setForm(f => ({
        ...f,
        producto_id: productoIdInicial.toString(),
        costo_unitario: producto?.precio_costo ? producto.precio_costo.toString() : f.costo_unitario,
        precio_venta: producto?.precio_venta ? producto.precio_venta.toString() : f.precio_venta,
        proveedor_id: producto?.proveedor_id ? producto.proveedor_id.toString() : f.proveedor_id
      }));
      setCppAplicado(null);
    }
  }, [open, productoIdInicial, productos]);

  useEffect(() => {
    if (!open) {
      setForm(emptyForm);
      setProductoSearch('');
      setCppAplicado(null);
    }
  }, [open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.producto_id || !almacenId || !form.cantidad) {
      toast.error('Complete todos los campos');
      return;
    }
    if (form.condicion_pago === 'credito' && !form.proveedor_id) {
      toast.error('Seleccione un proveedor para registrar la deuda a crédito');
      return;
    }

    try {
      const payload = {
        producto_id: parseInt(form.producto_id),
        almacen_id: almacenId,
        cantidad: parseInt(form.cantidad),
        tipo: 'ENTRADA',
        proveedor_id: form.proveedor_id ? parseInt(form.proveedor_id) : null,
        costo_unitario: form.costo_unitario ? parseFloat(form.costo_unitario) : null,
        costo_ponderado: cppAplicado,
        precio_venta: form.precio_venta ? parseFloat(form.precio_venta) : null,
        condicion_pago: form.condicion_pago || null,
        fecha_limite_pago: form.fecha_limite_pago || null,
        notas: form.notas || null
      };
      await api('/stock/entrada', { method: 'POST', body: JSON.stringify(payload) });
      if (form.condicion_pago === 'credito' && form.proveedor_id) {
        toast.success('Entrada registrada y deuda enviada al proveedor');
      } else {
        toast.success('Entrada registrada');
      }
      onOpenChange(false);
      onSuccess?.();
    } catch (e) {
      toast.error(e.message || 'Error al registrar entrada');
    }
  };

  const productoBloqueado = Boolean(productoIdInicial);

  // Stock y costo actuales del producto elegido, para el aviso y el cálculo de CPP
  const productoSeleccionado = productos.find(p => p.id.toString() === form.producto_id);
  const stockActual = productoSeleccionado?.stock_total || 0;
  const costoActual = productoSeleccionado?.precio_costo ? parseFloat(productoSeleccionado.precio_costo) : 0;
  const nuevaCantidad = parseInt(form.cantidad) || 0;
  const nuevoCosto = parseFloat(form.costo_unitario) || 0;
  const cpp = stockActual + nuevaCantidad > 0
    ? Math.round(((stockActual * costoActual) + (nuevaCantidad * nuevoCosto)) / (stockActual + nuevaCantidad))
    : nuevoCosto;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogDescription className="hidden">Formulario para registrar una entrada de stock</DialogDescription>
        <DialogHeader>
          <DialogTitle>Entrada de Stock</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Producto</Label>
            {productoBloqueado ? (
              <div className="flex h-10 w-full items-center rounded-md border border-input bg-muted/40 px-3 text-sm">
                {productos.find(p => p.id.toString() === form.producto_id)?.nombre || '...'}
              </div>
            ) : (
              <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    role="combobox"
                    aria-expanded={popoverOpen}
                    className="w-full justify-between"
                  >
                    {form.producto_id
                      ? productos.find((p) => p.id.toString() === form.producto_id)?.nombre
                      : "Buscar producto..."}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[400px] p-0">
                  <Command shouldFilter={false}>
                    <CommandInput
                      placeholder="Buscar por nombre o código..."
                      value={productoSearch}
                      onValueChange={setProductoSearch}
                    />
                    <CommandEmpty>No se encontró el producto.</CommandEmpty>
                    <CommandGroup className="max-h-64 overflow-auto">
                      {productos
                        .filter(p =>
                          !productoSearch ||
                          p.nombre.toLowerCase().includes(productoSearch.toLowerCase()) ||
                          p.codigo_barra?.toLowerCase().includes(productoSearch.toLowerCase())
                        )
                        .map((p) => (
                          <CommandItem
                            key={p.id}
                            value={p.nombre}
                            onSelect={() => {
                              setForm({
                                ...form,
                                producto_id: p.id.toString(),
                                costo_unitario: p.precio_costo ? p.precio_costo.toString() : '',
                                precio_venta: p.precio_venta ? p.precio_venta.toString() : '',
                                proveedor_id: p.proveedor_id ? p.proveedor_id.toString() : form.proveedor_id
                              });
                              setCppAplicado(null);
                              setPopoverOpen(false);
                              setProductoSearch('');
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                form.producto_id === p.id.toString() ? "opacity-100" : "opacity-0"
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
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Cantidad</Label>
              <Input
                type="number"
                min="1"
                value={form.cantidad}
                onChange={(e) => setForm({ ...form, cantidad: e.target.value })}
              />
            </div>
            <div>
              <Label>Precio de Costo (Gs.)</Label>
              <Input
                type="number"
                min="0"
                placeholder="0"
                value={form.costo_unitario}
                onChange={(e) => { setForm({ ...form, costo_unitario: e.target.value }); setCppAplicado(null); }}
              />
            </div>
          </div>
          {/* Aviso: el producto ya tiene stock */}
          {form.producto_id && stockActual > 0 && (
            <Alert variant="destructive" className="py-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                Este producto tiene <strong>{stockActual.toLocaleString('es-PY')} unidades</strong> en stock actualmente. ¿Estás seguro de que querés cargar una nueva tanda?
              </AlertDescription>
            </Alert>
          )}
          {/* CPP: visible cuando hay stock previo, cantidad y costo */}
          {form.producto_id && stockActual > 0 && form.cantidad && form.costo_unitario && (
            <div className="flex items-center gap-2 bg-muted/40 rounded px-3 py-2">
              <Calculator className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="flex-1 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">CPP:</span>{' '}
                ({stockActual} × {costoActual.toLocaleString('es-PY')} + {nuevaCantidad} × {nuevoCosto.toLocaleString('es-PY')}) ÷ {stockActual + nuevaCantidad}{' '}
                = <span className="font-mono font-semibold text-foreground">Gs. {cpp.toLocaleString('es-PY')}</span>
              </div>
              {cppAplicado === cpp ? (
                <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 font-semibold">
                  ✓ Aplicado
                  <button type="button" className="ml-1 opacity-60 hover:opacity-100" onClick={() => setCppAplicado(null)}>✕</button>
                </span>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="text-xs h-7 shrink-0"
                  onClick={() => setCppAplicado(cpp)}
                >
                  Aplicar
                </Button>
              )}
            </div>
          )}
          <div>
            <Label>Precio de Venta (Gs.) <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
            <Input
              type="number"
              min="0"
              placeholder="0"
              value={form.precio_venta}
              onChange={(e) => setForm({ ...form, precio_venta: e.target.value })}
            />
          </div>
          {form.costo_unitario && form.cantidad && (
            <div className="text-sm text-muted-foreground bg-muted/40 rounded px-3 py-2">
              Total compra: <span className="font-mono font-semibold">
                Gs. {(parseFloat(form.costo_unitario || 0) * parseInt(form.cantidad || 0)).toLocaleString('es-PY')}
              </span>
            </div>
          )}
          <div>
            <Label>Proveedor</Label>
            <Select value={form.proveedor_id} onValueChange={(v) => setForm({ ...form, proveedor_id: v })}>
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
                variant={form.condicion_pago === 'contado' ? 'default' : 'outline'}
                className="flex-1 gap-2"
                onClick={() => setForm({ ...form, condicion_pago: 'contado', fecha_limite_pago: '' })}
              >
                <ShoppingCart className="h-4 w-4" />
                Contado
              </Button>
              <Button
                type="button"
                variant={form.condicion_pago === 'credito' ? 'default' : 'outline'}
                className="flex-1 gap-2"
                onClick={() => setForm({ ...form, condicion_pago: 'credito' })}
              >
                <CreditCard className="h-4 w-4" />
                Crédito
              </Button>
            </div>
          </div>
          {form.condicion_pago === 'credito' && (
            <div>
              <Label>Fecha Límite de Pago</Label>
              <DatePickerInput
                value={form.fecha_limite_pago}
                onChange={(val) => setForm({ ...form, fecha_limite_pago: val })}
              />
            </div>
          )}
          <div>
            <Label>Notas (opcional)</Label>
            <Input
              placeholder="Ej: Factura #1234, lote especial..."
              value={form.notas}
              onChange={(e) => setForm({ ...form, notas: e.target.value })}
            />
          </div>
          <Button type="submit" className="w-full">Registrar Entrada</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EntradaStockDialog;
