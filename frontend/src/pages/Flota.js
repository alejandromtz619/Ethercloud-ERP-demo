import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
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
import { Car, Plus, Loader2, Edit, Trash2, Bike, Truck as TruckIcon, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const vehiculoIcons = {
  MOTO: Bike,
  AUTOMOVIL: Car,
  CAMIONETA: TruckIcon
};

const Flota = () => {
  const { api, empresa, userPermisos } = useApp();
  const [vehiculos, setVehiculos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    tipo: 'MOTO',
    chapa: '',
    vencimiento_habilitacion: '',
    vencimiento_cedula_verde: ''
  });

  const fetchVehiculos = async () => {
    if (!empresa?.id) return;
    try {
      const data = await api(`/vehiculos?empresa_id=${empresa.id}`);
      setVehiculos(data);
    } catch (e) {
      toast.error('Error al cargar vehículos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVehiculos();
  }, [empresa?.id]);

  const resetForm = () => {
    setFormData({
      tipo: 'MOTO',
      chapa: '',
      vencimiento_habilitacion: '',
      vencimiento_cedula_verde: ''
    });
    setEditingId(null);
  };

  const handleEdit = (vehiculo) => {
    setFormData({
      tipo: vehiculo.tipo,
      chapa: vehiculo.chapa,
      vencimiento_habilitacion: vehiculo.vencimiento_habilitacion || '',
      vencimiento_cedula_verde: vehiculo.vencimiento_cedula_verde || ''
    });
    setEditingId(vehiculo.id);
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.chapa) {
      toast.error('La chapa es requerida');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        ...formData,
        vencimiento_habilitacion: formData.vencimiento_habilitacion || null,
        vencimiento_cedula_verde: formData.vencimiento_cedula_verde || null
      };

      if (editingId) {
        await api(`/vehiculos/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        toast.success('Vehículo actualizado');
      } else {
        await api('/vehiculos', {
          method: 'POST',
          body: JSON.stringify({ ...payload, empresa_id: empresa.id })
        });
        toast.success('Vehículo creado');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchVehiculos();
    } catch (e) {
      toast.error(e.message || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Eliminar este vehículo?')) return;
    try {
      await api(`/vehiculos/${id}`, { method: 'DELETE' });
      toast.success('Vehículo eliminado');
      fetchVehiculos();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  const checkVencimiento = (fecha) => {
    if (!fecha) return null;
    const hoy = new Date();
    const venc = new Date(fecha);
    const dias = Math.ceil((venc - hoy) / (1000 * 60 * 60 * 24));
    
    if (dias < 0) return { status: 'vencido', dias: Math.abs(dias), color: 'destructive' };
    if (dias <= 7) return { status: 'urgente', dias, color: 'destructive' };
    if (dias <= 30) return { status: 'proximo', dias, color: 'warning' };
    return { status: 'ok', dias, color: 'success' };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="flota-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Flota de Vehículos</h1>
          <p className="text-muted-foreground">Gestión de vehículos y documentos</p>
        </div>
        {userPermisos.includes('flota.gestionar') && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="crear-vehiculo-btn">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Vehículo
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogDescription className="hidden">Formulario para crear o editar un vehículo</DialogDescription>
            <DialogHeader>
              <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Vehículo</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Tipo *</Label>
                <Select value={formData.tipo} onValueChange={(v) => setFormData({...formData, tipo: v})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MOTO">Moto</SelectItem>
                    <SelectItem value="AUTOMOVIL">Automóvil</SelectItem>
                    <SelectItem value="CAMIONETA">Camioneta</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Chapa *</Label>
                <Input
                  value={formData.chapa}
                  onChange={(e) => setFormData({...formData, chapa: e.target.value.toUpperCase()})}
                  placeholder="ABC-123"
                  className="uppercase"
                />
              </div>
              <div>
                <Label>Vencimiento Habilitación</Label>
                <Input
                  type="date"
                  value={formData.vencimiento_habilitacion}
                  onChange={(e) => setFormData({...formData, vencimiento_habilitacion: e.target.value})}
                />
              </div>
              <div>
                <Label>Vencimiento Cédula Verde</Label>
                <Input
                  type="date"
                  value={formData.vencimiento_cedula_verde}
                  onChange={(e) => setFormData({...formData, vencimiento_cedula_verde: e.target.value})}
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

      {/* Vehiculos Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {vehiculos.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="py-12 text-center">
              <Car className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No hay vehículos registrados</p>
            </CardContent>
          </Card>
        ) : (
          vehiculos.map((vehiculo) => {
            const Icon = vehiculoIcons[vehiculo.tipo] || Car;
            const habCheck = checkVencimiento(vehiculo.vencimiento_habilitacion);
            const cedulaCheck = checkVencimiento(vehiculo.vencimiento_cedula_verde);
            const hasAlert = habCheck?.status === 'vencido' || habCheck?.status === 'urgente' ||
                           cedulaCheck?.status === 'vencido' || cedulaCheck?.status === 'urgente';

            return (
              <Card key={vehiculo.id} className={cn("card-hover", hasAlert && "border-destructive")}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-12 h-12 rounded-full flex items-center justify-center",
                        hasAlert ? "bg-red-100 dark:bg-red-900/30" : "bg-primary/10"
                      )}>
                        <Icon className={cn(
                          "h-6 w-6",
                          hasAlert ? "text-red-600" : "text-primary"
                        )} />
                      </div>
                      <div>
                        <p className="font-bold text-lg">{vehiculo.chapa}</p>
                        <p className="text-sm text-muted-foreground capitalize">
                          {vehiculo.tipo.toLowerCase()}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {userPermisos.includes('flota.gestionar') && (
                        <>
                          <Button variant="ghost" size="icon" onClick={() => handleEdit(vehiculo)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(vehiculo.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Habilitación</span>
                      {vehiculo.vencimiento_habilitacion ? (
                        <Badge variant={habCheck?.color === 'success' ? 'secondary' : habCheck?.color}>
                          {habCheck?.status === 'vencido' ? `Vencido hace ${habCheck.dias}d` :
                           habCheck?.status === 'urgente' ? `Vence en ${habCheck.dias}d` :
                           habCheck?.status === 'proximo' ? `${habCheck.dias} días` :
                           new Date(vehiculo.vencimiento_habilitacion).toLocaleDateString('es-PY')}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">No definido</span>
                      )}
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">Cédula Verde</span>
                      {vehiculo.vencimiento_cedula_verde ? (
                        <Badge variant={cedulaCheck?.color === 'success' ? 'secondary' : cedulaCheck?.color}>
                          {cedulaCheck?.status === 'vencido' ? `Vencido hace ${cedulaCheck.dias}d` :
                           cedulaCheck?.status === 'urgente' ? `Vence en ${cedulaCheck.dias}d` :
                           cedulaCheck?.status === 'proximo' ? `${cedulaCheck.dias} días` :
                           new Date(vehiculo.vencimiento_cedula_verde).toLocaleDateString('es-PY')}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">No definido</span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
};

export default Flota;
