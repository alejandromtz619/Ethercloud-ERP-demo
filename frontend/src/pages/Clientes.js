import React, { useState, useEffect } from 'react';
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
import { Users, Plus, Loader2, Search, Edit, Trash2, CreditCard, DollarSign, Check } from 'lucide-react';
import { toast } from 'sonner';

const formatCurrency = (val) => {
  return new Intl.NumberFormat('es-PY', {
    style: 'currency',
    currency: 'PYG',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(val || 0);
};

const Clientes = () => {
  const { api, empresa, userPermisos } = useApp();
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creditoDialogOpen, setCreditoDialogOpen] = useState(false);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [creditos, setCreditos] = useState([]);
  const [creditoInfo, setCreditoInfo] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  const [pagoForm, setPagoForm] = useState({ credito_id: null, monto: '', observacion: '' });
  
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    ruc: '',
    cedula: '',
    direccion: '',
    telefono: '',
    email: '',
    acepta_cheque: false,
    descuento_porcentaje: '0',
    limite_credito: '1'
  });

  const fetchClientes = async () => {
    if (!empresa?.id) return;
    try {
      const data = await api(`/clientes?empresa_id=${empresa.id}`);
      setClientes(data);
    } catch (e) {
      toast.error('Error al cargar clientes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClientes();
  }, [empresa?.id]);

  const resetForm = () => {
    setFormData({
      nombre: '',
      apellido: '',
      ruc: '',
      cedula: '',
      direccion: '',
      telefono: '',
      email: '',
      acepta_cheque: false,
      descuento_porcentaje: '0',
      limite_credito: '1'
    });
    setEditingId(null);
  };

  const handleEdit = (cliente) => {
    setFormData({
      nombre: cliente.nombre,
      apellido: cliente.apellido || '',
      ruc: cliente.ruc || '',
      cedula: cliente.cedula || '',
      direccion: cliente.direccion || '',
      telefono: cliente.telefono || '',
      email: cliente.email || '',
      acepta_cheque: cliente.acepta_cheque || false,
      descuento_porcentaje: cliente.descuento_porcentaje?.toString() || '0',
      limite_credito: cliente.limite_credito?.toString() || '0'
    });
    setEditingId(cliente.id);
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
        descuento_porcentaje: parseFloat(formData.descuento_porcentaje) || 0,
        limite_credito: parseFloat(formData.limite_credito) || 0
      };

      if (editingId) {
        await api(`/clientes/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        toast.success('Cliente actualizado');
      } else {
        await api('/clientes', {
          method: 'POST',
          body: JSON.stringify({ ...payload, empresa_id: empresa.id })
        });
        toast.success('Cliente creado');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchClientes();
    } catch (e) {
      toast.error(e.message || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Desactivar este cliente?')) return;
    try {
      await api(`/clientes/${id}`, { method: 'DELETE' });
      toast.success('Cliente desactivado');
      fetchClientes();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  // Créditos functions
  const handleOpenCreditos = async (cliente) => {
    setSelectedCliente(cliente);
    setCreditoDialogOpen(true);
    await fetchCreditos(cliente.id);
  };

  const fetchCreditos = async (clienteId) => {
    try {
      const [creditosData, infoData] = await Promise.all([
        api(`/clientes/${clienteId}/creditos`),
        api(`/clientes/${clienteId}/credito-disponible`)
      ]);
      setCreditos(creditosData);
      setCreditoInfo(infoData);
    } catch (e) {
      toast.error('Error al cargar créditos');
    }
  };

  const handlePagarCredito = async (e) => {
    e.preventDefault();
    if (!pagoForm.monto || parseFloat(pagoForm.monto) <= 0) {
      toast.error('Ingrese un monto válido');
      return;
    }

    try {
      await api(`/creditos/${pagoForm.credito_id}/pagar`, {
        method: 'POST',
        body: JSON.stringify({
          monto: parseFloat(pagoForm.monto),
          observacion: pagoForm.observacion
        })
      });
      toast.success('Pago registrado');
      setPagoForm({ credito_id: null, monto: '', observacion: '' });
      await fetchCreditos(selectedCliente.id);
    } catch (e) {
      toast.error(e.message || 'Error al registrar pago');
    }
  };

  const filteredClientes = clientes.filter(c =>
    c.nombre.toLowerCase().includes(search.toLowerCase()) ||
    c.ruc?.toLowerCase().includes(search.toLowerCase()) ||
    c.telefono?.includes(search)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="clientes-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Clientes</h1>
          <p className="text-muted-foreground">Gestión de clientes y créditos</p>
        </div>
        {userPermisos.includes('clientes.crear') && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="crear-cliente-btn">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Cliente
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogDescription className="hidden">Formulario para crear o editar un cliente</DialogDescription>
            <DialogHeader>
              <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Cliente</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Nombre *</Label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                    data-testid="cliente-nombre"
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
                  <Label>RUC</Label>
                  <Input
                    value={formData.ruc}
                    onChange={(e) => setFormData({...formData, ruc: e.target.value})}
                    placeholder="Para facturación"
                    data-testid="cliente-ruc"
                  />
                </div>
                <div>
                  <Label>Cédula</Label>
                  <Input
                    value={formData.cedula}
                    onChange={(e) => setFormData({...formData, cedula: e.target.value})}
                  />
                </div>
                <div className="col-span-2">
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
                    data-testid="cliente-telefono"
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
                <div>
                  <Label>Descuento (%)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={formData.descuento_porcentaje}
                    onChange={(e) => setFormData({...formData, descuento_porcentaje: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Límite Crédito (Gs)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.limite_credito}
                    onChange={(e) => setFormData({...formData, limite_credito: e.target.value})}
                    placeholder="0 = sin límite"
                  />
                </div>
                <div className="flex items-center space-x-2 pt-6">
                  <Checkbox
                    id="acepta_cheque"
                    checked={formData.acepta_cheque}
                    onCheckedChange={(checked) => setFormData({...formData, acepta_cheque: checked})}
                  />
                  <Label htmlFor="acepta_cheque">Acepta Cheque</Label>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting} data-testid="guardar-cliente-btn">
                  {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  Guardar
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
        )}
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Listado ({filteredClientes.length})
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
                <TableHead>Cliente</TableHead>
                <TableHead>RUC</TableHead>
                <TableHead>Teléfono</TableHead>
                <TableHead>Descuento</TableHead>
                <TableHead>Límite Créd.</TableHead>
                <TableHead>Cheque</TableHead>
                <TableHead className="w-28">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredClientes.map((cliente) => (
                <TableRow key={cliente.id} data-testid={`cliente-row-${cliente.id}`}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{cliente.nombre} {cliente.apellido}</p>
                      {cliente.email && (
                        <p className="text-xs text-muted-foreground">{cliente.email}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{cliente.ruc || '-'}</TableCell>
                  <TableCell>{cliente.telefono || '-'}</TableCell>
                  <TableCell>
                    {cliente.descuento_porcentaje > 0 && (
                      <Badge className="badge-success">{cliente.descuento_porcentaje}%</Badge>
                    )}
                  </TableCell>
                  <TableCell className="font-mono-data text-sm">
                    {cliente.limite_credito > 0 ? formatCurrency(cliente.limite_credito) : '-'}
                  </TableCell>
                  <TableCell>
                    {cliente.acepta_cheque && <Badge className="badge-info">Sí</Badge>}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {userPermisos.includes('clientes.ver_creditos') && (
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          onClick={() => handleOpenCreditos(cliente)}
                          title="Ver créditos"
                        >
                          <CreditCard className="h-4 w-4" />
                        </Button>
                      )}
                      {userPermisos.includes('clientes.editar') && (
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(cliente)}>
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

      {/* Dialog de Créditos */}
      <Dialog open={creditoDialogOpen} onOpenChange={setCreditoDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogDescription className="hidden">Historial de créditos del cliente</DialogDescription>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Créditos - {selectedCliente?.nombre} {selectedCliente?.apellido || ''}
            </DialogTitle>
          </DialogHeader>
          
          {/* Summary */}
          {creditoInfo && (
            <div className="grid grid-cols-3 gap-4 p-4 bg-secondary rounded-lg">
              <div>
                <p className="text-xs text-muted-foreground">Límite</p>
                <p className="font-mono-data font-medium">
                  {formatCurrency(creditoInfo.limite_credito)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Usado</p>
                <p className="font-mono-data font-medium text-orange-600">
                  {formatCurrency(creditoInfo.credito_usado)}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Disponible</p>
                <p className="font-mono-data font-medium text-green-600">
                  {formatCurrency(creditoInfo.credito_disponible)}
                </p>
              </div>
            </div>
          )}
          
          <Separator />
          
          {/* Créditos List */}
          <ScrollArea className="h-96">
            <div className="space-y-3 pr-4">
              {creditos.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  Este cliente no tiene créditos registrados
                </p>
              ) : (
                creditos.map((credito) => (
                  <div 
                    key={credito.id} 
                    className={`p-4 border rounded-lg ${credito.pagado ? 'bg-muted/50' : 'bg-background'}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          {credito.venta_id && (
                            <Badge variant="outline">Venta #{credito.venta_id}</Badge>
                          )}
                          {credito.pagado ? (
                            <Badge className="badge-success">Pagado</Badge>
                          ) : (
                            <Badge variant="destructive">Pendiente</Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {credito.descripcion || 'Sin descripción'}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Fecha: {new Date(credito.fecha_venta).toLocaleDateString('es-PY')}
                        </p>
                        
                        {/* Pagos realizados */}
                        {credito.pagos && credito.pagos.length > 0 && (
                          <div className="mt-2 pt-2 border-t">
                            <p className="text-xs font-medium mb-1">Pagos realizados:</p>
                            {credito.pagos.map((pago) => (
                              <div key={pago.id} className="text-xs text-muted-foreground flex justify-between">
                                <span>{new Date(pago.fecha_pago).toLocaleDateString('es-PY')}</span>
                                <span className="font-mono">{formatCurrency(pago.monto)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">Original</p>
                        <p className="font-mono-data text-sm">{formatCurrency(credito.monto_original)}</p>
                        <p className="text-xs text-muted-foreground mt-2">Pendiente</p>
                        <p className="font-mono-data font-bold text-lg">
                          {formatCurrency(credito.monto_pendiente)}
                        </p>
                        
                        {!credito.pagado && (
                          <Button 
                            size="sm" 
                            className="mt-2"
                            onClick={() => setPagoForm({ 
                              credito_id: credito.id, 
                              monto: credito.monto_pendiente.toString(),
                              observacion: '' 
                            })}
                          >
                            <DollarSign className="h-4 w-4 mr-1" />
                            Cobrar
                          </Button>
                        )}
                      </div>
                    </div>
                    
                    {/* Formulario de pago inline */}
                    {pagoForm.credito_id === credito.id && (
                      <form onSubmit={handlePagarCredito} className="mt-4 pt-4 border-t">
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <Label className="text-xs">Monto a cobrar</Label>
                            <Input
                              type="number"
                              value={pagoForm.monto}
                              onChange={(e) => setPagoForm({...pagoForm, monto: e.target.value})}
                              max={credito.monto_pendiente}
                            />
                          </div>
                          <div className="col-span-2">
                            <Label className="text-xs">Observación</Label>
                            <Input
                              value={pagoForm.observacion}
                              onChange={(e) => setPagoForm({...pagoForm, observacion: e.target.value})}
                              placeholder="Opcional"
                            />
                          </div>
                        </div>
                        <div className="flex gap-2 mt-2">
                          <Button type="submit" size="sm">
                            <Check className="h-4 w-4 mr-1" />
                            Registrar Pago
                          </Button>
                          <Button 
                            type="button" 
                            variant="outline" 
                            size="sm"
                            onClick={() => setPagoForm({ credito_id: null, monto: '', observacion: '' })}
                          >
                            Cancelar
                          </Button>
                        </div>
                      </form>
                    )}
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Clientes;
