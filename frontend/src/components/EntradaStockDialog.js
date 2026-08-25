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
import { ChevronsUpDown, Check, ShoppingCart, CreditCard } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import { DatePickerInput } from './ui/date-picker-input';

const ALMACEN_DEFAULT_NOMBRE = 'Tienda';

const emptyForm = {
  producto_id: '',
  cantidad: '',
  proveedor_id: '',
  costo_unitario: '',
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
        proveedor_id: producto?.proveedor_id ? producto.proveedor_id.toString() : f.proveedor_id
      }));
    }
  }, [open, productoIdInicial, productos]);

  useEffect(() => {
    if (!open) {
      setForm(emptyForm);
      setProductoSearch('');
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
                                proveedor_id: p.proveedor_id ? p.proveedor_id.toString() : form.proveedor_id
                              });
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
                onChange={(e) => setForm({ ...form, costo_unitario: e.target.value })}
              />
            </div>
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
