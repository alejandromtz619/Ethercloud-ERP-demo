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
import { Building2, Plus, Loader2, Search, Edit, Trash2, DollarSign, Check, BarChart2, ExternalLink, ArrowUpDown, Download } from 'lucide-react';
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

  // ── Comparación de Mercado handlers ──────────────────────────────
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

  const formatPYG = (v) => '₲ ' + Math.round(v).toLocaleString('es-PY');

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
      <Dialog open={deudaDialogOpen} onOpenChange={setDeudaDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Deudas - {selectedProveedor?.nombre}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Summary */}
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
            
            {/* Deudas List */}
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
                <TableHead className="w-32">Acciones</TableHead>
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
                                      {precio.costo !== null ? formatPYG(precio.costo) : <span className="text-muted-foreground text-xs">Sin precio</span>}
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
                                {precio.costo !== null ? formatPYG(precio.costo) : <span className="text-muted-foreground text-xs">Sin precio</span>}
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
    </div>
  );
};

export default Proveedores;
