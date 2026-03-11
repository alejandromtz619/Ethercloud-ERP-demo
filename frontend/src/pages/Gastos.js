import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '../components/ui/dialog';
import { Receipt, Plus, Loader2, Search, Edit, Trash2, RefreshCw, DollarSign } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const formatPYG = (value) => {
  if (value === null || value === undefined) return '₲ 0';
  return `₲ ${Math.round(Number(value)).toLocaleString('es-PY')}`;
};

const EMPTY_FORM = {
  monto: '',
  responsable_nombre: '',
  fecha: new Date().toISOString().split('T')[0],
  motivo: '',
};

const Gastos = () => {
  const { api, empresa, userPermisos } = useApp();
  const [gastos, setGastos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  const canEdit = userPermisos?.includes('gastos.gestionar') || userPermisos?.includes('admin');

  const fetchGastos = useCallback(async () => {
    if (!empresa?.id) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ empresa_id: empresa.id });
      if (fechaDesde) params.append('fecha_desde', fechaDesde);
      if (fechaHasta) params.append('fecha_hasta', fechaHasta);
      const data = await api(`/gastos?${params.toString()}`);
      setGastos(data);
    } catch (e) {
      toast.error('Error al cargar gastos');
    } finally {
      setLoading(false);
    }
  }, [api, empresa?.id, fechaDesde, fechaHasta]);

  useEffect(() => { fetchGastos(); }, [fetchGastos]);

  const resetForm = () => { setForm(EMPTY_FORM); setEditingId(null); };

  const openCreate = () => { resetForm(); setDialogOpen(true); };

  const handleEdit = (g) => {
    setForm({
      monto: String(g.monto),
      responsable_nombre: g.responsable_nombre,
      fecha: g.fecha,
      motivo: g.motivo,
    });
    setEditingId(g.id);
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.monto || !form.responsable_nombre || !form.fecha || !form.motivo) {
      toast.error('Todos los campos son requeridos');
      return;
    }
    if (isNaN(Number(form.monto)) || Number(form.monto) <= 0) {
      toast.error('El monto debe ser un número positivo');
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        monto: Number(form.monto),
        responsable_nombre: form.responsable_nombre.trim(),
        fecha: form.fecha,
        motivo: form.motivo.trim(),
      };
      if (editingId) {
        await api(`/gastos/${editingId}`, { method: 'PUT', body: JSON.stringify(payload) });
        toast.success('Gasto actualizado');
      } else {
        await api('/gastos', { method: 'POST', body: JSON.stringify({ ...payload, empresa_id: empresa.id }) });
        toast.success('Gasto registrado');
      }
      setDialogOpen(false);
      resetForm();
      fetchGastos();
    } catch (e) {
      toast.error(e.message || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este gasto?')) return;
    try {
      await api(`/gastos/${id}`, { method: 'DELETE' });
      toast.success('Gasto eliminado');
      fetchGastos();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  const filtered = gastos.filter(g =>
    g.motivo.toLowerCase().includes(search.toLowerCase()) ||
    g.responsable_nombre.toLowerCase().includes(search.toLowerCase())
  );

  const totalFiltrado = filtered.reduce((sum, g) => sum + Number(g.monto), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-muted">
            <Receipt className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Gastos Operativos</h1>
            <p className="text-muted-foreground text-sm">Registro de gastos de la empresa</p>
          </div>
        </div>
        {canEdit && (
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo Gasto
          </Button>
        )}
      </div>

      {/* Totals summary */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Desde</Label>
              <Input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="h-8 text-sm w-40" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hasta</Label>
              <Input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="h-8 text-sm w-40" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Motivo o responsable…"
                  className="h-8 text-sm pl-7 w-48"
                />
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={fetchGastos} disabled={loading} className="h-8 gap-1">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Actualizar
            </Button>
            <div className="ml-auto flex items-center gap-2 bg-muted/50 px-4 py-2 rounded-lg">
              <DollarSign className="h-4 w-4 text-red-500" />
              <div>
                <p className="text-xs text-muted-foreground">Total en vista</p>
                <p className="text-sm font-bold font-mono text-red-600">{formatPYG(totalFiltrado)}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Listado de gastos</CardTitle>
          <CardDescription className="text-xs">{filtered.length} registro{filtered.length !== 1 ? 's' : ''}</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-32 text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" /> Cargando…
            </div>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-12">
              {gastos.length === 0 ? 'No hay gastos registrados.' : 'Sin resultados para la búsqueda.'}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs">Fecha</th>
                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs">Motivo</th>
                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground text-xs">Responsable</th>
                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground text-xs">Monto</th>
                    {canEdit && <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground text-xs">Acciones</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filtered.map(g => (
                    <tr key={g.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-2.5 text-muted-foreground whitespace-nowrap">
                        {new Date(g.fecha + 'T00:00:00').toLocaleDateString('es-PY')}
                      </td>
                      <td className="px-4 py-2.5 font-medium max-w-xs">{g.motivo}</td>
                      <td className="px-4 py-2.5 text-muted-foreground">{g.responsable_nombre}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold text-red-600">
                        {formatPYG(g.monto)}
                      </td>
                      {canEdit && (
                        <td className="px-4 py-2.5 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleEdit(g)}>
                              <Edit className="h-3.5 w-3.5" />
                            </Button>
                            <Button size="icon" variant="ghost" className="h-7 w-7 text-red-500 hover:text-red-700" onClick={() => handleDelete(g.id)}>
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Gasto Operativo</DialogTitle>
            <DialogDescription>
              Registrá un gasto de la empresa (agua, combustible, limpieza, etc.)
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-sm">Monto (₲) *</Label>
                <Input
                  type="number"
                  value={form.monto}
                  onChange={e => setForm(f => ({ ...f, monto: e.target.value }))}
                  placeholder="Ej: 150000"
                  min="1"
                  step="1"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-sm">Fecha *</Label>
                <Input
                  type="date"
                  value={form.fecha}
                  onChange={e => setForm(f => ({ ...f, fecha: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Motivo / Descripción *</Label>
              <Input
                value={form.motivo}
                onChange={e => setForm(f => ({ ...f, motivo: e.target.value }))}
                placeholder="Ej: Reposición bidones de agua"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-sm">Responsable *</Label>
              <Input
                value={form.responsable_nombre}
                onChange={e => setForm(f => ({ ...f, responsable_nombre: e.target.value }))}
                placeholder="Nombre del responsable"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {editingId ? 'Actualizar' : 'Registrar'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Gastos;
