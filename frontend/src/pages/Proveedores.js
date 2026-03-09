import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
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
import { Building2, Plus, Loader2, Search, Edit, Trash2, DollarSign, Check, Link2, BarChart2, ExternalLink, ArrowUpDown, Download, ClipboardList } from 'lucide-react';
import { toast } from 'sonner';
import { DatePickerInput } from '../components/ui/date-picker-input';

const Proveedores = () => {
  const { api, empresa, userPermisos } = useApp();
  const [proveedores, setProveedores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deudaDialogOpen, setDeudaDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [selectedProveedor, setSelectedProveedor] = useState(null);
  const [deudas, setDeudas] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');

  // Vincular dialog
  const [vincularOpen, setVincularOpen] = useState(false);
  const [vincularProveedor, setVincularProveedor] = useState(null);
  const [vinculaciones, setVinculaciones] = useState([]);
  const [productos, setProductos] = useState([]);
  const [productosSearch, setProductosSearch] = useState('');
  const [editingVinculacion, setEditingVinculacion] = useState(null);
  const [vincularForm, setVincularForm] = useState({ producto_id: '', sku: '', costo: '', link: '' });
  const [vincularSubmitting, setVincularSubmitting] = useState(false);

  // Comparación de Mercado
  const [comparacionOpen, setComparacionOpen] = useState(false);
  const [comparacionData, setComparacionData] = useState(null);
  const [comparacionLoading, setComparacionLoading] = useState(false);
  const [sortProveedor, setSortProveedor] = useState(null); // proveedor id to sort by
  const [sortDirection, setSortDirection] = useState('asc');
  const [comparacionSearch, setComparacionSearch] = useState('');
  const [activeCell, setActiveCell] = useState(null); // {prod_id, prov_id}
  const [exportingExcel, setExportingExcel] = useState(false);
  const [rankMode, setRankMode] = useState(false); // per-row ranked columns

  // Generar Pedido
  const [pedidoOpen, setPedidoOpen] = useState(false);
  const [pedidoProveedor, setPedidoProveedor] = useState(null);
  const [pedidoProductos, setPedidoProductos] = useState([]); // [{...vinculacion, selected, cantidad}]
  const [pedidoComparacion, setPedidoComparacion] = useState(null);
  const [pedidoLoading, setPedidoLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    nombre: '',
    ruc: '',
    direccion: '',
    telefono: '',
    email: ''
  });

  const [deudaForm, setDeudaForm] = useState({
    monto: '',
    descripcion: '',
    fecha_limite: ''
  });

  const fetchProveedores = async () => {
    if (!empresa?.id) return;
    try {
      const data = await api(`/proveedores?empresa_id=${empresa.id}`);
      setProveedores(data);
    } catch (e) {
      toast.error('Error al cargar proveedores');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProveedores();
  }, [empresa?.id]);

  const resetForm = () => {
    setFormData({ nombre: '', ruc: '', direccion: '', telefono: '', email: '' });
    setEditingId(null);
  };

  const handleEdit = (proveedor) => {
    setFormData({
      nombre: proveedor.nombre,
      ruc: proveedor.ruc || '',
      direccion: proveedor.direccion || '',
      telefono: proveedor.telefono || '',
      email: proveedor.email || ''
    });
    setEditingId(proveedor.id);
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.nombre) {
      toast.error('El nombre es requerido');
      return;
    }
    
    setSubmitting(true);
    try {
      if (editingId) {
        await api(`/proveedores/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(formData)
        });
        toast.success('Proveedor actualizado');
      } else {
        await api('/proveedores', {
          method: 'POST',
          body: JSON.stringify({ ...formData, empresa_id: empresa.id })
        });
        toast.success('Proveedor creado');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchProveedores();
    } catch (e) {
      toast.error(e.message || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Desactivar este proveedor?')) return;
    try {
      await api(`/proveedores/${id}`, { method: 'DELETE' });
      toast.success('Proveedor desactivado');
      fetchProveedores();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  const fetchDeudas = async (proveedorId) => {
    try {
      const data = await api(`/proveedores/${proveedorId}/deudas`);
      setDeudas(data);
    } catch (e) {
      toast.error('Error al cargar deudas');
    }
  };

  const handleVerDeudas = (proveedor) => {
    setSelectedProveedor(proveedor);
    fetchDeudas(proveedor.id);
    setDeudaDialogOpen(true);
  };

  const handleCrearDeuda = async (e) => {
    e.preventDefault();
    if (!deudaForm.monto) {
      toast.error('El monto es requerido');
      return;
    }

    try {
      await api(`/proveedores/${selectedProveedor.id}/deudas`, {
        method: 'POST',
        body: JSON.stringify({
          monto: parseFloat(deudaForm.monto),
          descripcion: deudaForm.descripcion,
          fecha_limite: deudaForm.fecha_limite || null
        })
      });
      toast.success('Deuda registrada');
      setDeudaForm({ monto: '', descripcion: '', fecha_limite: '' });
      fetchDeudas(selectedProveedor.id);
    } catch (e) {
      toast.error('Error al crear deuda');
    }
  };

  const handlePagarDeuda = async (deudaId) => {
    try {
      await api(`/deudas/${deudaId}/pagar`, { method: 'PUT' });
      toast.success('Deuda pagada');
      fetchDeudas(selectedProveedor.id);
    } catch (e) {
      toast.error('Error al pagar deuda');
    }
  };

  const handleEliminarDeuda = async (deudaId) => {
    if (!window.confirm('¿Eliminar esta deuda permanentemente? Esta acción no se puede deshacer.')) return;
    try {
      await api(`/deudas/${deudaId}`, { method: 'DELETE' });
      toast.success('Deuda eliminada');
      fetchDeudas(selectedProveedor.id);
    } catch (e) {
      toast.error('Error al eliminar deuda');
    }
  };

  // ── Vincular handlers ──────────────────────────────────────────────
  const fetchVinculaciones = async (proveedorId) => {
    try {
      const data = await api(`/proveedores/${proveedorId}/productos`);
      setVinculaciones(data);
    } catch (e) {
      toast.error('Error al cargar productos vinculados');
    }
  };

  const fetchProductos = async () => {
    if (!empresa?.id) return;
    try {
      const data = await api(`/productos?empresa_id=${empresa.id}`);
      setProductos(data);
    } catch (e) {
      // non-blocking
    }
  };

  const handleAbrirVincular = (proveedor) => {
    setVincularProveedor(proveedor);
    setVincularForm({ producto_id: '', sku: '', costo: '', link: '' });
    setEditingVinculacion(null);
    setProductosSearch('');
    fetchVinculaciones(proveedor.id);
    fetchProductos();
    setVincularOpen(true);
  };

  const handleVincularSubmit = async (e) => {
    e.preventDefault();
    if (!vincularForm.producto_id) {
      toast.error('Seleccioná un producto');
      return;
    }
    setVincularSubmitting(true);
    try {
      if (editingVinculacion) {
        await api(`/proveedor-productos/${editingVinculacion.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            sku: vincularForm.sku || null,
            costo: vincularForm.costo ? parseFloat(vincularForm.costo) : null,
            link: vincularForm.link || null,
          })
        });
        toast.success('Vinculación actualizada');
      } else {
        await api(`/proveedores/${vincularProveedor.id}/productos`, {
          method: 'POST',
          body: JSON.stringify({
            producto_id: parseInt(vincularForm.producto_id),
            sku: vincularForm.sku || null,
            costo: vincularForm.costo ? parseFloat(vincularForm.costo) : null,
            link: vincularForm.link || null,
          })
        });
        toast.success('Producto vinculado');
      }
      setVincularForm({ producto_id: '', sku: '', costo: '', link: '' });
      setEditingVinculacion(null);
      fetchVinculaciones(vincularProveedor.id);
    } catch (e) {
      toast.error(e.message || 'Error al vincular producto');
    } finally {
      setVincularSubmitting(false);
    }
  };

  const handleEditarVinculacion = (v) => {
    setEditingVinculacion(v);
    setVincularForm({
      producto_id: v.producto_id,
      sku: v.sku || '',
      costo: v.costo !== null && v.costo !== undefined ? String(v.costo) : '',
      link: v.link || '',
    });
  };

  const handleEliminarVinculacion = async (id) => {
    if (!window.confirm('¿Eliminar esta vinculación?')) return;
    try {
      await api(`/proveedor-productos/${id}`, { method: 'DELETE' });
      toast.success('Vinculación eliminada');
      fetchVinculaciones(vincularProveedor.id);
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  // ── Comparación de Mercado handlers ───────────────────────────────
  const handleAbrirComparacion = async () => {
    setComparacionOpen(true);
    setComparacionLoading(true);
    try {
      const data = await api(`/proveedores/comparacion-mercado?empresa_id=${empresa.id}`);
      setComparacionData(data);
    } catch (e) {
      toast.error('Error al cargar comparación');
    } finally {
      setComparacionLoading(false);
    }
  };

  const handleSortByProveedor = (provId) => {
    if (sortProveedor === provId) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortProveedor(provId);
      setSortDirection('asc');
    }
  };

  const getSortedFilas = () => {
    if (!comparacionData) return [];
    let filas = [...comparacionData.filas];
    if (comparacionSearch) {
      filas = filas.filter(f => f.producto_nombre.toLowerCase().includes(comparacionSearch.toLowerCase()));
    }
    if (sortProveedor !== null) {
      filas.sort((a, b) => {
        const pa = a.precios[String(sortProveedor)]?.costo ?? Infinity;
        const pb = b.precios[String(sortProveedor)]?.costo ?? Infinity;
        return sortDirection === 'asc' ? pa - pb : pb - pa;
      });
    }
    return filas;
  };

  // ── Generar Pedido handlers ───────────────────────────────────────
  const handleAbrirPedido = async (proveedor) => {
    setPedidoProveedor(proveedor);
    setPedidoLoading(true);
    setPedidoOpen(true);
    try {
      const [vincs, comp] = await Promise.all([
        api(`/proveedores/${proveedor.id}/productos`),
        api(`/proveedores/comparacion-mercado?empresa_id=${empresa.id}`),
      ]);
      setPedidoProductos(vincs.map(v => ({ ...v, selected: false, cantidad: 1 })));
      setPedidoComparacion(comp);
    } catch (e) {
      toast.error('Error al cargar productos');
    } finally {
      setPedidoLoading(false);
    }
  };

  const getPedidoPrecioAlert = (vinc) => {
    if (!pedidoComparacion || vinc.costo === null || vinc.costo === undefined) return null;
    const fila = pedidoComparacion.filas.find(f => f.producto_id === vinc.producto_id);
    if (!fila) return null;
    const precios = Object.entries(fila.precios)
      .filter(([, p]) => p.costo !== null)
      .sort((a, b) => a[1].costo - b[1].costo);
    if (precios.length === 0) return null;
    const [bestProvId, bestPrecio] = precios[0];
    const esBestProv = String(pedidoProveedor.id) === bestProvId;
    if (esBestProv) return { tipo: 'mejor', diff: null };
    const bestProvNombre = pedidoComparacion.proveedores.find(p => String(p.id) === bestProvId)?.nombre;
    const diff = parseFloat(vinc.costo) - bestPrecio.costo;
    return { tipo: 'caro', diff, bestProvNombre, bestCosto: bestPrecio.costo };
  };

  const handleGenerarPedidoPDF = () => {
    const seleccionados = pedidoProductos.filter(p => p.selected && p.cantidad > 0);
    if (seleccionados.length === 0) {
      toast.error('Seleccioná al menos un producto');
      return;
    }
    const fecha = new Date().toLocaleDateString('es-PY', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const filas = seleccionados.map(p => {
      const skuCell = p.sku ? `<td>${p.sku}</td>` : '<td>—</td>';
      const linkCell = p.link
        ? `<td style="word-break:break-all;font-size:8px;"><a href="${p.link}">${p.link}</a></td>`
        : '<td>—</td>';
      return `<tr><td>${p.producto_nombre}</td>${skuCell}<td style="text-align:center">${p.cantidad}</td>${linkCell}</tr>`;
    }).join('');
    const hasLinks = seleccionados.some(p => p.link);
    const colWidths = hasLinks
      ? 'style="width:35%"' : '';
    const printWindow = window.open('', '_blank');
    if (!printWindow) { toast.error('Bloqueado por el navegador. Permitir popups.'); return; }
    printWindow.document.write(`<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Pedido – ${pedidoProveedor.nombre}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, sans-serif; font-size: 11px; color: #111; padding: 24px; }
  header { border-bottom: 2px solid #0044CC; padding-bottom: 10px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-end; }
  header h1 { font-size: 18px; color: #0044CC; font-weight: bold; }
  header .meta { text-align: right; font-size: 10px; color: #555; }
  table { width: 100%; border-collapse: collapse; margin-top: 8px; }
  th { background: #0044CC; color: #fff; padding: 7px 8px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; }
  td { padding: 6px 8px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
  tr:nth-child(even) td { background: #f5f7ff; }
  .qty { text-align: center; font-weight: bold; }
  footer { margin-top: 24px; font-size: 9px; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 8px; }
  @media print {
    body { padding: 0; }
    a { color: #0044CC; }
    @page { margin: 15mm 12mm; }
  }
</style>
</head>
<body>
<header>
  <div>
    <h1>Pedido a Proveedor</h1>
    <div style="font-size:13px;margin-top:4px;font-weight:bold">${pedidoProveedor.nombre}</div>
    ${pedidoProveedor.ruc ? `<div style="font-size:10px;color:#555">RUC: ${pedidoProveedor.ruc}</div>` : ''}
    ${pedidoProveedor.email ? `<div style="font-size:10px;color:#555">${pedidoProveedor.email}</div>` : ''}
    ${pedidoProveedor.telefono ? `<div style="font-size:10px;color:#555">Tel: ${pedidoProveedor.telefono}</div>` : ''}
  </div>
  <div class="meta">
    <div>Fecha: <strong>${fecha}</strong></div>
    <div>Productos: <strong>${seleccionados.length}</strong></div>
  </div>
</header>
<table>
  <thead><tr>
    <th ${colWidths}>Producto</th>
    <th style="width:15%">SKU Proveedor</th>
    <th style="width:8%;text-align:center">Cantidad</th>
    ${hasLinks ? '<th>Enlace</th>' : ''}
  </tr></thead>
  <tbody>${filas}</tbody>
</table>
<footer>Generado por Ethercloud ERP · ${fecha}</footer>
</body></html>`);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => { printWindow.print(); printWindow.close(); }, 400);
  };

  const handleExportarExcel = async () => {
    setExportingExcel(true);
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/proveedores/comparacion-mercado/excel?empresa_id=${empresa.id}`,
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      if (!response.ok) throw new Error('Error al exportar');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'comparacion_mercado.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error('Error al exportar Excel');
    } finally {
      setExportingExcel(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PY', {
      style: 'currency',
      currency: 'PYG',
      minimumFractionDigits: 0
    }).format(value);
  };

  const filteredProveedores = proveedores.filter(p =>
    p.nombre.toLowerCase().includes(search.toLowerCase()) ||
    p.ruc?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="proveedores-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Proveedores</h1>
          <p className="text-muted-foreground">Gestión de proveedores y deudas</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleAbrirComparacion}>
            <BarChart2 className="mr-2 h-4 w-4" />
            Comparación de Mercado
          </Button>
          {userPermisos.includes('proveedores.crear') && (
            <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
              <DialogTrigger asChild>
                <Button data-testid="crear-proveedor-btn">
                  <Plus className="mr-2 h-4 w-4" />
                  Nuevo Proveedor
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogDescription className="hidden">Formulario para crear o editar un proveedor</DialogDescription>
                <DialogHeader>
                  <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Proveedor</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <Label>Nombre *</Label>
                    <Input
                      value={formData.nombre}
                      onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                      data-testid="proveedor-nombre"
                    />
                  </div>
                  <div>
                    <Label>RUC</Label>
                    <Input
                      value={formData.ruc}
                      onChange={(e) => setFormData({...formData, ruc: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Dirección</Label>
                    <Input
                      value={formData.direccion}
                      onChange={(e) => setFormData({...formData, direccion: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Teléfono</Label>
                    <Input
                      value={formData.telefono}
                      onChange={(e) => setFormData({...formData, telefono: e.target.value})}
                    />
                  </div>
                  <div>
                    <Label>Email</Label>
                    <Input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({...formData, email: e.target.value})}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                      Cancelar
                    </Button>
                    <Button type="submit" disabled={submitting}>
                      {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                      Guardar
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>

      {/* Deudas Dialog */}
      <Dialog open={deudaDialogOpen} onOpenChange={setDeudaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Deudas - {selectedProveedor?.nombre}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 p-4 bg-secondary rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground">Total Pendiente</p>
                <p className="font-mono-data font-medium text-orange-600">
                  {formatCurrency(deudas.filter(d => !d.pagado).reduce((sum, d) => sum + parseFloat(d.monto), 0))}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Pagado</p>
                <p className="font-mono-data font-medium text-green-600">
                  {formatCurrency(deudas.filter(d => d.pagado).reduce((sum, d) => sum + parseFloat(d.monto), 0))}
                </p>
              </div>
            </div>
            <form onSubmit={handleCrearDeuda} className="space-y-3 p-3 border rounded-lg">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs">Monto *</Label>
                  <Input
                    type="number"
                    placeholder="Monto"
                    value={deudaForm.monto}
                    onChange={(e) => setDeudaForm({...deudaForm, monto: e.target.value})}
                  />
                </div>
                <div>
                  <Label className="text-xs">Fecha Límite</Label>
                  <DatePickerInput
                    value={deudaForm.fecha_limite}
                    onChange={(val) => setDeudaForm({...deudaForm, fecha_limite: val})}
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs">Descripción</Label>
                <Input
                  placeholder="Descripción de la deuda"
                  value={deudaForm.descripcion}
                  onChange={(e) => setDeudaForm({...deudaForm, descripcion: e.target.value})}
                />
              </div>
              <Button type="submit" className="w-full" size="sm">
                <Plus className="h-4 w-4 mr-1" /> Registrar Deuda
              </Button>
            </form>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {deudas.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">Sin deudas registradas</p>
              ) : (
                deudas.map((deuda) => (
                  <div key={deuda.id} className="p-3 bg-secondary rounded-lg">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-mono-data font-medium">{formatCurrency(deuda.monto)}</p>
                        <p className="text-xs text-muted-foreground">{deuda.descripcion || 'Sin descripción'}</p>
                        <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                          <span>Emitida: {new Date(deuda.creado_en).toLocaleDateString('es-PY')}</span>
                          {deuda.fecha_limite && (
                            <span className={new Date(deuda.fecha_limite) < new Date() && !deuda.pagado ? 'text-destructive' : ''}>
                              Vence: {new Date(deuda.fecha_limite).toLocaleDateString('es-PY')}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {deuda.pagado ? (
                          <div className="text-right">
                            <Badge className="badge-success">Pagado</Badge>
                            {deuda.fecha_pago && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {new Date(deuda.fecha_pago).toLocaleDateString('es-PY')}
                              </p>
                            )}
                          </div>
                        ) : (
                          <Button size="sm" onClick={() => handlePagarDeuda(deuda.id)}>
                            <Check className="h-4 w-4 mr-1" /> Pagar
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10 px-2"
                          onClick={() => handleEliminarDeuda(deuda.id)}
                          title="Eliminar deuda"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Vincular Productos Dialog */}
      <Dialog open={vincularOpen} onOpenChange={(open) => { setVincularOpen(open); if (!open) { setEditingVinculacion(null); setVincularForm({ producto_id: '', sku: '', costo: '', link: '' }); } }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogDescription className="hidden">Vincular productos a proveedor</DialogDescription>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              Vincular Productos — {vincularProveedor?.nombre}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Form */}
            <form onSubmit={handleVincularSubmit} className="p-3 border rounded-lg space-y-3">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {editingVinculacion ? 'Editar vinculación' : 'Nueva vinculación'}
              </p>
              {/* Selector de producto */}
              {!editingVinculacion && (
                <div>
                  <Label className="text-xs">Producto *</Label>
                  <div className="relative mt-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Buscar producto..."
                      className="pl-8 text-sm"
                      value={productosSearch}
                      onChange={(e) => setProductosSearch(e.target.value)}
                    />
                  </div>
                  {productosSearch && (
                    <div className="border rounded-lg mt-1 max-h-40 overflow-y-auto bg-background z-10 relative">
                      {productos
                        .filter(p =>
                          p.nombre.toLowerCase().includes(productosSearch.toLowerCase()) ||
                          p.codigo_barra?.toLowerCase().includes(productosSearch.toLowerCase())
                        )
                        .filter(p => !vinculaciones.find(v => v.producto_id === p.id))
                        .slice(0, 20)
                        .map(p => (
                          <button
                            key={p.id}
                            type="button"
                            className="w-full text-left px-3 py-2 text-sm hover:bg-secondary flex items-center justify-between"
                            onClick={() => {
                              setVincularForm(f => ({ ...f, producto_id: p.id }));
                              setProductosSearch(p.nombre);
                            }}
                          >
                            <span>{p.nombre}</span>
                            {p.codigo_barra && <span className="text-xs text-muted-foreground font-mono">{p.codigo_barra}</span>}
                          </button>
                        ))
                      }
                      {productos.filter(p =>
                        p.nombre.toLowerCase().includes(productosSearch.toLowerCase()) ||
                        p.codigo_barra?.toLowerCase().includes(productosSearch.toLowerCase())
                      ).filter(p => !vinculaciones.find(v => v.producto_id === p.id)).length === 0 && (
                        <p className="text-center text-xs text-muted-foreground py-3">Sin resultados</p>
                      )}
                    </div>
                  )}
                  {vincularForm.producto_id && (
                    <p className="text-xs text-green-600 mt-1">
                      ✓ {productos.find(p => p.id === vincularForm.producto_id)?.nombre || 'Producto seleccionado'}
                    </p>
                  )}
                </div>
              )}
              {editingVinculacion && (
                <div>
                  <Label className="text-xs">Producto</Label>
                  <p className="text-sm font-medium mt-1 p-2 bg-secondary rounded">{editingVinculacion.producto_nombre}</p>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs">SKU del Proveedor</Label>
                  <Input
                    placeholder="Ej: PROV-12345"
                    value={vincularForm.sku}
                    onChange={(e) => setVincularForm(f => ({ ...f, sku: e.target.value }))}
                    className="text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Costo (₲) <span className="text-muted-foreground">— opcional</span></Label>
                  <Input
                    type="number"
                    placeholder="Precio de compra"
                    value={vincularForm.costo}
                    onChange={(e) => setVincularForm(f => ({ ...f, costo: e.target.value }))}
                    className="text-sm"
                  />
                </div>
              </div>
              <div>
                <Label className="text-xs">Enlace al producto <span className="text-muted-foreground">— opcional</span></Label>
                <Input
                  type="url"
                  placeholder="https://..."
                  value={vincularForm.link}
                  onChange={(e) => setVincularForm(f => ({ ...f, link: e.target.value }))}
                  className="text-sm"
                />
              </div>
              <div className="flex gap-2 justify-end">
                {editingVinculacion && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => { setEditingVinculacion(null); setVincularForm({ producto_id: '', sku: '', costo: '', link: '' }); }}>
                    Cancelar edición
                  </Button>
                )}
                <Button type="submit" size="sm" disabled={vincularSubmitting}>
                  {vincularSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
                  {editingVinculacion ? 'Guardar cambios' : 'Vincular Producto'}
                </Button>
              </div>
            </form>

            {/* Vinculaciones list */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                Productos vinculados ({vinculaciones.length})
              </p>
              {vinculaciones.length === 0 ? (
                <p className="text-center text-sm text-muted-foreground py-6">Sin productos vinculados aún</p>
              ) : (
                <div className="space-y-2">
                  {vinculaciones.map((v) => (
                    <div key={v.id} className="p-3 bg-secondary rounded-lg flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{v.producto_nombre}</p>
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-0.5">
                          {v.sku && (
                            <span className="text-xs font-mono text-muted-foreground">SKU: {v.sku}</span>
                          )}
                          {v.costo !== null && v.costo !== undefined && (
                            <span className="text-xs font-mono text-blue-600">{formatCurrency(v.costo)}</span>
                          )}
                          {v.link && (
                            <a
                              href={v.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary flex items-center gap-1 hover:underline"
                            >
                              <ExternalLink className="h-3 w-3" /> Ver en proveedor
                            </a>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleEditarVinculacion(v)}
                          title="Editar"
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive"
                          onClick={() => handleEliminarVinculacion(v.id)}
                          title="Eliminar"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Comparación de Mercado Dialog */}
      <Dialog open={comparacionOpen} onOpenChange={setComparacionOpen}>
        <DialogContent className="max-w-[95vw] w-full max-h-[92vh] flex flex-col">
          <DialogDescription className="hidden">Comparación de precios por proveedor</DialogDescription>
          <DialogHeader className="shrink-0">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <DialogTitle className="flex items-center gap-2">
                <BarChart2 className="h-5 w-5" />
                Comparación de Mercado
              </DialogTitle>
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    placeholder="Filtrar producto..."
                    className="pl-8 h-8 text-sm w-52"
                    value={comparacionSearch}
                    onChange={(e) => setComparacionSearch(e.target.value)}
                  />
                </div>
                <Button
                  size="sm"
                  variant={rankMode ? 'default' : 'outline'}
                  onClick={() => { setRankMode(r => !r); setActiveCell(null); }}
                  title="Muestra los proveedores de cada producto ordenados de menor a mayor precio"
                >
                  <ArrowUpDown className="h-3.5 w-3.5 mr-1" />
                  {rankMode ? 'Ranking activo' : 'Por precio ↑'}
                </Button>
                <Button size="sm" variant="outline" onClick={handleExportarExcel} disabled={exportingExcel || comparacionLoading}>
                  {exportingExcel ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> : <Download className="h-3.5 w-3.5 mr-1" />}
                  Excel
                </Button>
              </div>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-auto min-h-0">
            {comparacionLoading ? (
              <div className="flex items-center justify-center h-40">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : !comparacionData || comparacionData.filas.length === 0 ? (
              <div className="text-center text-muted-foreground py-12">
                <BarChart2 className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p>No hay productos vinculados a proveedores todavía.</p>
                <p className="text-sm mt-1">Usá el botón <strong>Vincular</strong> en cada proveedor para asociar productos.</p>
              </div>
            ) : rankMode ? (
              // ── Modo ranking por precio: columnas por fila ordenadas de menor a mayor ──
              (() => {
                const filas = getSortedFilas();
                const maxCols = comparacionData.proveedores.length;
                const rankHeaders = Array.from({ length: maxCols }, (_, i) =>
                  i === 0 ? '1° más barato' : i === 1 ? '2°' : i === 2 ? '3°' : `${i + 1}°`
                );
                return (
                  <table className="w-full text-sm border-collapse">
                    <thead className="sticky top-0 z-10">
                      <tr>
                        <th className="text-left px-3 py-2 bg-secondary border border-border font-semibold min-w-[200px] sticky left-0 z-20">
                          Producto
                        </th>
                        {rankHeaders.map((h, i) => (
                          <th key={i} className={`px-3 py-2 bg-secondary border border-border font-semibold min-w-[160px] text-center ${i === 0 ? 'text-green-500' : ''}`}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filas.map((fila, ri) => {
                        // Sort this row's providers by price asc, nulls last
                        const rankedProvs = comparacionData.proveedores
                          .map(prov => ({ prov, precio: fila.precios[String(prov.id)] || null }))
                          .filter(x => x.precio !== null)
                          .sort((a, b) => {
                            const ca = a.precio.costo ?? Infinity;
                            const cb = b.precio.costo ?? Infinity;
                            return ca - cb;
                          });
                        // Pad to maxCols with nulls
                        const cells = [...rankedProvs, ...Array(maxCols - rankedProvs.length).fill(null)];
                        return (
                          <tr key={fila.producto_id} className={ri % 2 === 0 ? '' : 'bg-secondary/30'}>
                            <td className="px-3 py-2 border border-border font-medium sticky left-0 bg-background z-10">
                              {fila.producto_nombre}
                            </td>
                            {cells.map((cell, ci) => {
                              if (!cell) {
                                return (
                                  <td key={ci} className="px-3 py-2 border border-border text-center text-muted-foreground text-xs">—</td>
                                );
                              }
                              const { prov, precio } = cell;
                              const isActive = activeCell?.prod_id === fila.producto_id && activeCell?.prov_id === prov.id;
                              const isCheapest = ci === 0;
                              return (
                                <td
                                  key={ci}
                                  className={`px-3 py-2 border border-border cursor-pointer transition-colors ${
                                    isActive ? 'bg-primary/10 ring-1 ring-inset ring-primary' : isCheapest ? 'bg-green-500/5 hover:bg-green-500/10' : 'hover:bg-muted'
                                  }`}
                                  onClick={() => setActiveCell(isActive ? null : { prod_id: fila.producto_id, prov_id: prov.id })}
                                >
                                  <div className="space-y-0.5">
                                    <div className={`text-xs font-semibold ${isCheapest ? 'text-green-500' : 'text-muted-foreground'}`}>
                                      {prov.nombre}
                                    </div>
                                    <div className="font-mono font-medium text-sm text-right">
                                      {precio.costo !== null ? formatCurrency(precio.costo) : <span className="text-muted-foreground text-xs">Sin precio</span>}
                                    </div>
                                    {isActive && (
                                      <div className="space-y-1 pt-1 border-t border-border/50">
                                        {precio.sku && (
                                          <div className="text-xs text-muted-foreground font-mono">
                                            SKU: <span className="text-foreground">{precio.sku}</span>
                                          </div>
                                        )}
                                        {precio.link && (
                                          <a
                                            href={precio.link}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-primary flex items-center gap-1 hover:underline"
                                            onClick={(e) => e.stopPropagation()}
                                          >
                                            <ExternalLink className="h-3 w-3" /> Ver en sitio
                                          </a>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                );
              })()
            ) : (
              // ── Modo estándar: columna fija por proveedor ──
              <table className="w-full text-sm border-collapse">
                <thead className="sticky top-0 z-10">
                  <tr>
                    <th className="text-left px-3 py-2 bg-secondary border border-border font-semibold min-w-[200px] sticky left-0 z-20">
                      Producto
                    </th>
                    {comparacionData.proveedores.map(prov => (
                      <th
                        key={prov.id}
                        className="px-3 py-2 bg-secondary border border-border font-semibold min-w-[140px] cursor-pointer hover:bg-muted select-none"
                        onClick={() => handleSortByProveedor(prov.id)}
                      >
                        <div className="flex items-center justify-center gap-1">
                          <span>{prov.nombre}</span>
                          <ArrowUpDown className={`h-3.5 w-3.5 shrink-0 ${sortProveedor === prov.id ? 'text-primary' : 'text-muted-foreground'}`} />
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {getSortedFilas().map((fila, ri) => (
                    <tr key={fila.producto_id} className={ri % 2 === 0 ? '' : 'bg-secondary/30'}>
                      <td className="px-3 py-2 border border-border font-medium sticky left-0 bg-background z-10">
                        {fila.producto_nombre}
                      </td>
                      {comparacionData.proveedores.map(prov => {
                        const precio = fila.precios[String(prov.id)];
                        const isActive = activeCell?.prod_id === fila.producto_id && activeCell?.prov_id === prov.id;
                        if (!precio) {
                          return (
                            <td key={prov.id} className="px-3 py-2 border border-border text-center text-muted-foreground text-xs">
                              —
                            </td>
                          );
                        }
                        return (
                          <td
                            key={prov.id}
                            className={`px-3 py-2 border border-border text-right cursor-pointer transition-colors ${isActive ? 'bg-primary/10 ring-1 ring-inset ring-primary' : 'hover:bg-muted'}`}
                            onClick={() => setActiveCell(isActive ? null : { prod_id: fila.producto_id, prov_id: prov.id })}
                          >
                            <div className="space-y-0.5">
                              <div className="font-mono font-medium text-sm">
                                {precio.costo !== null ? formatCurrency(precio.costo) : <span className="text-muted-foreground text-xs">Sin precio</span>}
                              </div>
                              {isActive && (
                                <div className="text-left space-y-1 pt-1 border-t border-border/50">
                                  {precio.sku && (
                                    <div className="text-xs text-muted-foreground font-mono">
                                      SKU: <span className="text-foreground">{precio.sku}</span>
                                    </div>
                                  )}
                                  {precio.link && (
                                    <a
                                      href={precio.link}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-xs text-primary flex items-center gap-1 hover:underline"
                                      onClick={(e) => e.stopPropagation()}
                                    >
                                      <ExternalLink className="h-3 w-3" /> Ver en sitio
                                    </a>
                                  )}
                                </div>
                              )}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {comparacionData && (
            <div className="shrink-0 pt-2 border-t border-border text-xs text-muted-foreground flex items-center gap-2">
              <span>{getSortedFilas().length} producto(s)</span>
              {rankMode ? (
                <span>• Modo ranking: columnas ordenadas de menor a mayor precio por producto</span>
              ) : sortProveedor !== null && (
                <span>• Ordenado por: <strong>{comparacionData.proveedores.find(p => p.id === sortProveedor)?.nombre}</strong> ({sortDirection === 'asc' ? '↑ menor precio' : '↓ mayor precio'})</span>
              )}
              <span className="ml-auto">Clic en una celda para ver SKU y enlace</span>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Generar Pedido Dialog */}
      <Dialog open={pedidoOpen} onOpenChange={setPedidoOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
          <DialogDescription className="hidden">Generar pedido a proveedor</DialogDescription>
          <DialogHeader className="shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              Generar Pedido — {pedidoProveedor?.nombre}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto min-h-0 space-y-3 py-2">
            {pedidoLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : pedidoProductos.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground text-sm">
                <Link2 className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p>No hay productos vinculados a este proveedor.</p>
                <p className="text-xs mt-1">Usá el botón <strong>Vincular</strong> para agregar productos.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {/* Select All bar */}
                <div className="flex items-center justify-between px-1 pb-2 border-b">
                  <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded"
                      checked={pedidoProductos.length > 0 && pedidoProductos.every(p => p.selected)}
                      onChange={(e) => setPedidoProductos(prev => prev.map(p => ({ ...p, selected: e.target.checked })))}
                    />
                    <span className="text-muted-foreground text-xs font-medium uppercase tracking-wide">Seleccionar todos</span>
                  </label>
                  <span className="text-xs text-muted-foreground">
                    {pedidoProductos.filter(p => p.selected).length} de {pedidoProductos.length} seleccionado(s)
                  </span>
                </div>

                {pedidoProductos.map((p, idx) => {
                  const alerta = getPedidoPrecioAlert(p);
                  return (
                    <div
                      key={p.id}
                      className={`rounded-lg border p-3 transition-colors ${p.selected ? 'border-primary/40 bg-primary/5' : 'border-border bg-muted/20'}`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 rounded cursor-pointer"
                          checked={p.selected}
                          onChange={(e) => setPedidoProductos(prev => prev.map((item, i) => i === idx ? { ...item, selected: e.target.checked } : item))}
                        />
                        <div className="flex-1 min-w-0 space-y-1.5">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <span className="font-medium text-sm">{p.producto_nombre}</span>
                            {p.sku && (
                              <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                SKU: {p.sku}
                              </span>
                            )}
                          </div>

                          {alerta && (
                            alerta.tipo === 'mejor' ? (
                              <div className="inline-flex items-center gap-1 text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded px-2 py-0.5">
                                <Check className="h-3 w-3" />
                                Mejor precio en este proveedor
                              </div>
                            ) : (
                              <div className="inline-flex items-center gap-1 flex-wrap text-xs text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800 rounded px-2 py-0.5">
                                ⚠ Más barato en <strong>{alerta.bestProvNombre}</strong>
                                {' · '}Gs. {Math.round(alerta.bestCosto).toLocaleString('es-PY')}
                                {' · '}ahorrás Gs. {Math.round(alerta.diff).toLocaleString('es-PY')}
                              </div>
                            )
                          )}

                          <div className="flex items-center gap-2">
                            <label className="text-xs text-muted-foreground">Cantidad:</label>
                            <Input
                              type="number"
                              min="1"
                              value={p.cantidad}
                              onChange={(e) => {
                                const val = Math.max(1, parseInt(e.target.value) || 1);
                                setPedidoProductos(prev => prev.map((item, i) => i === idx ? { ...item, cantidad: val } : item));
                              }}
                              className="h-7 w-20 text-sm"
                            />
                            {p.link && (
                              <a
                                href={p.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="ml-auto text-xs text-primary flex items-center gap-1 hover:underline"
                              >
                                <ExternalLink className="h-3 w-3" /> Ver producto
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {!pedidoLoading && pedidoProductos.length > 0 && (
            <div className="shrink-0 pt-3 border-t flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                {pedidoProductos.filter(p => p.selected).length === 0
                  ? 'Seleccioná los productos para incluir en el pedido'
                  : `${pedidoProductos.filter(p => p.selected).length} producto(s) en el pedido`}
              </p>
              <Button
                onClick={handleGenerarPedidoPDF}
                disabled={pedidoProductos.filter(p => p.selected).length === 0}
                className="gap-2"
              >
                <ClipboardList className="h-4 w-4" />
                Generar PDF
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Listado ({filteredProveedores.length})
            </CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="table-compact">
                <TableHead>Proveedor</TableHead>
                <TableHead>RUC</TableHead>
                <TableHead>Teléfono</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="w-36">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredProveedores.map((proveedor) => (
                <TableRow key={proveedor.id}>
                  <TableCell>
                    <p className="font-medium">{proveedor.nombre}</p>
                    {proveedor.direccion && (
                      <p className="text-xs text-muted-foreground">{proveedor.direccion}</p>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{proveedor.ruc || '-'}</TableCell>
                  <TableCell>{proveedor.telefono || '-'}</TableCell>
                  <TableCell>{proveedor.email || '-'}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Generar pedido"
                        onClick={() => handleAbrirPedido(proveedor)}
                      >
                        <ClipboardList className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Vincular productos"
                        onClick={() => handleAbrirVincular(proveedor)}
                      >
                        <Link2 className="h-4 w-4" />
                      </Button>
                      {userPermisos.includes('proveedores.gestionar_deudas') && (
                        <Button variant="ghost" size="icon" onClick={() => handleVerDeudas(proveedor)}>
                          <DollarSign className="h-4 w-4" />
                        </Button>
                      )}
                      {userPermisos.includes('proveedores.editar') && (
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(proveedor)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default Proveedores;
