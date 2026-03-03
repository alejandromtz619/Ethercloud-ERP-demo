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
import { UserCog, Plus, Loader2, Search, Edit, Trash2, Wallet, Check } from 'lucide-react';
import { toast } from 'sonner';
import { DatePickerInput } from '../components/ui/date-picker-input';

const Funcionarios = () => {
  const { api, empresa, userPermisos } = useApp();
  const [funcionarios, setFuncionarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [adelantoDialogOpen, setAdelantoDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [selectedFuncionario, setSelectedFuncionario] = useState(null);
  const [adelantos, setAdelantos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    cedula: '',
    cargo: '',
    salario_base: '',
    ips: '',
    fecha_nacimiento: ''
  });

  const [adelantoMonto, setAdelantoMonto] = useState('');

  const fetchFuncionarios = async () => {
    if (!empresa?.id) return;
    try {
      const data = await api(`/funcionarios?empresa_id=${empresa.id}`);
      setFuncionarios(data);
    } catch (e) {
      toast.error('Error al cargar funcionarios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFuncionarios();
  }, [empresa?.id]);

  const resetForm = () => {
    setFormData({
      nombre: '',
      apellido: '',
      cedula: '',
      cargo: '',
      salario_base: '',
      ips: '',
      fecha_nacimiento: ''
    });
    setEditingId(null);
  };

  const handleEdit = (funcionario) => {
    setFormData({
      nombre: funcionario.nombre,
      apellido: funcionario.apellido || '',
      cedula: funcionario.cedula || '',
      cargo: funcionario.cargo || '',
      salario_base: funcionario.salario_base?.toString() || '',
      ips: funcionario.ips?.toString() || '',
      fecha_nacimiento: funcionario.fecha_nacimiento || ''
    });
    setEditingId(funcionario.id);
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
      const payload = {
        ...formData,
        salario_base: parseFloat(formData.salario_base) || 0,
        ips: formData.ips ? parseFloat(formData.ips) : null,
        fecha_nacimiento: formData.fecha_nacimiento || null
      };

      if (editingId) {
        await api(`/funcionarios/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        toast.success('Funcionario actualizado');
      } else {
        await api('/funcionarios', {
          method: 'POST',
          body: JSON.stringify({ ...payload, empresa_id: empresa.id })
        });
        toast.success('Funcionario creado');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchFuncionarios();
    } catch (e) {
      toast.error(e.message || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Desactivar este funcionario?')) return;
    try {
      await api(`/funcionarios/${id}`, { method: 'DELETE' });
      toast.success('Funcionario desactivado');
      fetchFuncionarios();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  const fetchAdelantos = async (funcionarioId) => {
    const periodo = new Date().toISOString().slice(0, 7); // YYYY-MM
    try {
      const data = await api(`/funcionarios/${funcionarioId}/adelantos?periodo=${periodo}`);
      setAdelantos(data);
    } catch (e) {
      toast.error('Error al cargar adelantos');
    }
  };

  const handleVerAdelantos = (funcionario) => {
    setSelectedFuncionario(funcionario);
    fetchAdelantos(funcionario.id);
    setAdelantoDialogOpen(true);
  };

  const handleCrearAdelanto = async (e) => {
    e.preventDefault();
    if (!adelantoMonto) {
      toast.error('El monto es requerido');
      return;
    }

    try {
      await api(`/funcionarios/${selectedFuncionario.id}/adelantos`, {
        method: 'POST',
        body: JSON.stringify({ monto: parseFloat(adelantoMonto) })
      });
      toast.success('Adelanto registrado');
      setAdelantoMonto('');
      fetchAdelantos(selectedFuncionario.id);
    } catch (e) {
      toast.error('Error al crear adelanto');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PY', {
      style: 'currency',
      currency: 'PYG',
      minimumFractionDigits: 0
    }).format(value);
  };

  // Calculate total adelantos
  const totalAdelantos = adelantos.reduce((sum, a) => sum + parseFloat(a.monto), 0);
  const salarioRestante = selectedFuncionario ? 
    parseFloat(selectedFuncionario.salario_base || 0) - totalAdelantos : 0;

  const filteredFuncionarios = funcionarios.filter(f =>
    f.nombre.toLowerCase().includes(search.toLowerCase()) ||
    f.apellido?.toLowerCase().includes(search.toLowerCase()) ||
    f.cedula?.includes(search)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="funcionarios-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Funcionarios</h1>
          <p className="text-muted-foreground">Gestión de personal y adelantos</p>
        </div>
        {userPermisos.includes('funcionarios.crear') && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="crear-funcionario-btn">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Funcionario
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogDescription className="hidden">Formulario para crear o editar un funcionario</DialogDescription>
            <DialogHeader>
              <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Funcionario</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Nombre *</Label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Apellido</Label>
                  <Input
                    value={formData.apellido}
                    onChange={(e) => setFormData({...formData, apellido: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Cédula</Label>
                  <Input
                    value={formData.cedula}
                    onChange={(e) => setFormData({...formData, cedula: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Cargo</Label>
                  <Input
                    value={formData.cargo}
                    onChange={(e) => setFormData({...formData, cargo: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Salario Base (Gs.)</Label>
                  <Input
                    type="number"
                    value={formData.salario_base}
                    onChange={(e) => setFormData({...formData, salario_base: e.target.value})}
                  />
                </div>
                <div>
                  <Label>IPS (Gs.) - Opcional</Label>
                  <Input
                    type="number"
                    value={formData.ips}
                    onChange={(e) => setFormData({...formData, ips: e.target.value})}
                  />
                </div>
                <div className="col-span-2">
                  <Label>Fecha Nacimiento</Label>
                  <DatePickerInput
                    value={formData.fecha_nacimiento}
                    onChange={(val) => setFormData({...formData, fecha_nacimiento: val})}
                  />
                </div>
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

      {/* Adelantos Dialog */}
      <Dialog open={adelantoDialogOpen} onOpenChange={setAdelantoDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              Adelantos - {selectedFuncionario?.nombre} {selectedFuncionario?.apellido}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-3 gap-4 p-4 bg-secondary rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground">Salario Base</p>
                <p className="font-mono-data font-medium">
                  {formatCurrency(selectedFuncionario?.salario_base || 0)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Adelantos</p>
                <p className="font-mono-data font-medium text-orange-600">
                  {formatCurrency(totalAdelantos)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Restante</p>
                <p className="font-mono-data font-medium text-green-600">
                  {formatCurrency(salarioRestante)}
                </p>
              </div>
            </div>

            {/* New Adelanto Form */}
            {userPermisos.includes('funcionarios.adelantos') && (
              <form onSubmit={handleCrearAdelanto} className="flex gap-2">
                <Input
                  type="number"
                  placeholder="Monto del adelanto"
                  value={adelantoMonto}
                  onChange={(e) => setAdelantoMonto(e.target.value)}
                  className="flex-1"
                />
                <Button type="submit">
                  <Plus className="h-4 w-4 mr-1" /> Adelanto
                </Button>
              </form>
            )}
            
            {/* Adelantos List */}
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {adelantos.length === 0 ? (
                <p className="text-center text-muted-foreground py-4">
                  Sin adelantos este mes
                </p>
              ) : (
                adelantos.map((adelanto) => (
                  <div key={adelanto.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                    <div>
                      <p className="font-mono-data font-medium">{formatCurrency(adelanto.monto)}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(adelanto.creado_en).toLocaleDateString('es-PY')}
                      </p>
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
              <UserCog className="h-5 w-5" />
              Listado ({filteredFuncionarios.length})
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
                <TableHead>Funcionario</TableHead>
                <TableHead>Cédula</TableHead>
                <TableHead>Cargo</TableHead>
                <TableHead>Salario Base</TableHead>
                <TableHead>Adelantos Mes</TableHead>
                <TableHead>Restante</TableHead>
                <TableHead className="w-28">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredFuncionarios.map((funcionario) => (
                <TableRow key={funcionario.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{funcionario.nombre} {funcionario.apellido}</p>
                      {funcionario.fecha_nacimiento && (
                        <p className="text-xs text-muted-foreground">
                          Cumpleaños: {new Date(funcionario.fecha_nacimiento).toLocaleDateString('es-PY')}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{funcionario.cedula || '-'}</TableCell>
                  <TableCell>{funcionario.cargo || '-'}</TableCell>
                  <TableCell className="font-mono-data">{formatCurrency(funcionario.salario_base)}</TableCell>
                  <TableCell className="font-mono-data text-orange-600">
                    {funcionario.total_adelantos_mes > 0 ? formatCurrency(funcionario.total_adelantos_mes) : '-'}
                  </TableCell>
                  <TableCell className="font-mono-data font-semibold text-green-600">
                    {formatCurrency(funcionario.salario_restante)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {userPermisos.includes('funcionarios.ver_salarios') && (
                        <Button variant="ghost" size="icon" onClick={() => handleVerAdelantos(funcionario)}>
                          <Wallet className="h-4 w-4" />
                        </Button>
                      )}
                      {userPermisos.includes('funcionarios.editar') && (
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(funcionario)}>
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

export default Funcionarios;
