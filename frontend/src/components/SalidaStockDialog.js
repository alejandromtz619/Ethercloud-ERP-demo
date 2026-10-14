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
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from './ui/command';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { ChevronsUpDown, Check } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const ALMACEN_DEFAULT_NOMBRE = 'Tienda';

const emptyForm = {
  producto_id: '',
  cantidad: '',
  motivo: ''
};

// Dialog de salida/eliminación de stock reutilizable desde Stock.js y Productos.js.
// El almacén se resuelve automáticamente a "Tienda" (único almacén operativo)
// y nunca se muestra al usuario.
const SalidaStockDialog = ({ open, onOpenChange, productoIdInicial, onSuccess }) => {
  const { api, empresa } = useApp();
  const [productos, setProductos] = useState([]);
  const [almacenId, setAlmacenId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [productoSearch, setProductoSearch] = useState('');

  useEffect(() => {
    if (!open || !empresa?.id) return;
    (async () => {
      try {
        const [productosData, almacenesData] = await Promise.all([
          api(`/productos?empresa_id=${empresa.id}`),
          api(`/almacenes?empresa_id=${empresa.id}`)
        ]);
        setProductos(productosData);
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
      setForm(f => ({ ...f, producto_id: productoIdInicial.toString() }));
    }
  }, [open, productoIdInicial]);

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

    try {
      await api('/stock/salida', {
        method: 'POST',
        body: JSON.stringify({
          producto_id: parseInt(form.producto_id),
          almacen_id: almacenId,
          cantidad: parseInt(form.cantidad),
          motivo: form.motivo || 'Salida manual'
        })
      });
      toast.success('Salida registrada');
      onOpenChange(false);
      onSuccess?.();
    } catch (e) {
      toast.error(e.message || 'Error al registrar salida');
    }
  };

  const productoBloqueado = Boolean(productoIdInicial);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogDescription className="hidden">Formulario para registrar una salida o eliminación de stock</DialogDescription>
        <DialogHeader>
          <DialogTitle>Salida/Eliminación de Stock</DialogTitle>
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
                              setForm({ ...form, producto_id: p.id.toString() });
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
            <Label>Motivo</Label>
            <Input
              value={form.motivo}
              onChange={(e) => setForm({ ...form, motivo: e.target.value })}
              placeholder="Ej: Producto dañado, vencido, etc."
            />
          </div>
          <Button type="submit" variant="destructive" className="w-full">Registrar Salida</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default SalidaStockDialog;
