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
import ProductoCombobox from './ProductoCombobox';
import { toast } from 'sonner';

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
  const [productoSel, setProductoSel] = useState(null);
  const [almacenId, setAlmacenId] = useState(null);
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    if (!open || !empresa?.id) return;
    (async () => {
      try {
        const almacenesData = await api(`/almacenes?empresa_id=${empresa.id}`);
        const tienda = almacenesData.find(a => a.nombre === ALMACEN_DEFAULT_NOMBRE && a.estado !== false);
        const activo = tienda || almacenesData.find(a => a.estado !== false) || almacenesData[0];
        setAlmacenId(activo?.id || null);
      } catch (e) {
        toast.error('Error al cargar datos');
      }
    })();
  }, [open, empresa?.id]);

  const elegirProducto = (producto) => {
    setProductoSel(producto);
    setForm(f => ({ ...f, producto_id: producto.id.toString() }));
  };

  useEffect(() => {
    if (!open || !productoIdInicial) return;
    (async () => {
      try {
        elegirProducto(await api(`/productos/${productoIdInicial}`));
      } catch (e) {
        toast.error('Error al cargar el producto');
      }
    })();
  }, [open, productoIdInicial]);

  useEffect(() => {
    if (!open) {
      setForm(emptyForm);
      setProductoSel(null);
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
                {productoSel?.nombre || '...'}
              </div>
            ) : (
              <ProductoCombobox value={productoSel} onChange={elegirProducto} />
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
