import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Truck, Loader2, Filter, User, Phone, Package, MapPin, Edit, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const estadoColors = {
  PENDIENTE: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400 border-yellow-300',
  EN_CAMINO: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border-blue-300',
  ENTREGADO: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 border-green-300',
  CANCELADO: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 border-red-300'
};

const Delivery = () => {
  const { api, empresa, userPermisos } = useApp();
  const [entregas, setEntregas] = useState([]);
  const [vehiculos, setVehiculos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [entregaSeleccionada, setEntregaSeleccionada] = useState(null);
  const [ventaDetalles, setVentaDetalles] = useState(null);
  const [loadingDetalles, setLoadingDetalles] = useState(false);
  
  // Form states
  const [vehiculoId, setVehiculoId] = useState('');
  const [responsableId, setResponsableId] = useState('');
  
  // Confirmation dialog
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [accionConfirmar, setAccionConfirmar] = useState(null);
  
  const [filtros, setFiltros] = useState({
    fechaDesde: '',
    fechaHasta: '',
    vehiculoId: 'all',
    responsableId: 'all',
    estado: 'all'
  });

  const fetchData = async () => {
    if (!empresa?.id) return;
    try {
      let url = `/entregas?empresa_id=${empresa.id}`;
      if (filtros.fechaDesde) url += `&fecha_desde=${filtros.fechaDesde}`;
      if (filtros.fechaHasta) url += `&fecha_hasta=${filtros.fechaHasta}`;
      if (filtros.vehiculoId && filtros.vehiculoId !== 'all') url += `&vehiculo_id=${filtros.vehiculoId}`;
      if (filtros.responsableId && filtros.responsableId !== 'all') url += `&responsable_id=${filtros.responsableId}`;
      if (filtros.estado && filtros.estado !== 'all') url += `&estado=${filtros.estado}`;
      
      const [entregasData, vehiculosData, usuariosData] = await Promise.all([
        api(url),
        api(`/vehiculos?empresa_id=${empresa.id}`),
        api(`/usuarios?empresa_id=${empresa.id}`)
      ]);
      
      setEntregas(entregasData);
      setVehiculos(vehiculosData);
      setUsuarios(usuariosData);
    } catch (e) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [empresa?.id, filtros]);

  const handleCardClick = async (entrega) => {
    setEntregaSeleccionada(entrega);
    setVehiculoId(entrega.vehiculo_id?.toString() || '');
    setResponsableId(entrega.responsable_usuario_id?.toString() || '');
    
    // Open modal - data already loaded from entregas endpoint
    setLoadingDetalles(false);
    setModalOpen(true);
    
    // Use entrega items if available, otherwise fetch venta details
    if (!entrega.items || entrega.items.length === 0) {
      setLoadingDetalles(true);
      try {
        const detalles = await api(`/ventas/${entrega.venta_id}`);
        setVentaDetalles(detalles);
      } catch (e) {
        toast.error('Error al cargar detalles');
      } finally {
        setLoadingDetalles(false);
      }
    } else {
      // Use entrega data as venta details
      setVentaDetalles({
        id: entrega.venta_id,
        total: entrega.items.reduce((sum, item) => sum + item.total, 0),
        items: entrega.items,
        cliente_nombre: entrega.cliente_nombre,
        cliente_telefono: entrega.cliente_telefono,
        cliente_direccion: entrega.cliente_direccion
      });
    }
  };

  const handleAsignar = async () => {
    if (!vehiculoId || !responsableId) {
      toast.error('Debe seleccionar vehículo y responsable');
      return;
    }

    try {
      await api(`/entregas/${entregaSeleccionada.id}/asignar`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vehiculo_id: parseInt(vehiculoId),
          responsable_usuario_id: parseInt(responsableId)
        })
      });
      toast.success(entregaSeleccionada.estado === 'PENDIENTE' ? 'Entrega asignada y en camino' : 'Entrega actualizada');
      setModalOpen(false);
      fetchData();
    } catch (e) {
      toast.error('Error al asignar entrega');
    }
  };

  const handleMarcarEntregado = () => {
    setAccionConfirmar({
      titulo: '¿Marcar como entregado?',
      descripcion: '¿Estás seguro de que quieres marcar este pedido como entregado?',
      accion: async () => {
        try {
          await api(`/entregas/${entregaSeleccionada.id}/estado?estado=ENTREGADO`, {
            method: 'PUT'
          });
          toast.success('Pedido marcado como entregado');
          setModalOpen(false);
          fetchData();
        } catch (e) {
          toast.error('Error al actualizar estado');
        }
      }
    });
    setConfirmDialogOpen(true);
  };

  const handleEliminarEntrega = () => {
    setAccionConfirmar({
      titulo: '¿Eliminar orden de delivery?',
      descripcion: 'Esta acción no se puede deshacer. La venta asociada no será eliminada.',
      accion: async () => {
        try {
          await api(`/entregas/${entregaSeleccionada.id}`, {
            method: 'DELETE'
          });
          toast.success('Orden de delivery eliminada');
          setModalOpen(false);
          fetchData();
        } catch (e) {
          toast.error(e.message || 'Error al eliminar entrega');
        }
      }
    });
    setConfirmDialogOpen(true);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PY', {
      style: 'currency',
      currency: 'PYG',
      minimumFractionDigits: 0
    }).format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  const entregasPendientes = entregas.filter(e => e.estado === 'PENDIENTE');
  const entregasEnCamino = entregas.filter(e => e.estado === 'EN_CAMINO');
  const entregasFinalizadas = entregas.filter(e => e.estado === 'ENTREGADO');

  return (
    <div className="space-y-6" data-testid="delivery-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Delivery</h1>
          <p className="text-muted-foreground">Gestión de entregas y pedidos</p>
        </div>
      </div>

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <Label>Fecha Desde</Label>
              <Input
                type="date"
                value={filtros.fechaDesde}
                onChange={(e) => setFiltros({...filtros, fechaDesde: e.target.value})}
              />
            </div>
            <div>
              <Label>Fecha Hasta</Label>
              <Input
                type="date"
                value={filtros.fechaHasta}
                onChange={(e) => setFiltros({...filtros, fechaHasta: e.target.value})}
              />
            </div>
            <div>
              <Label>Vehículo</Label>
              <Select value={filtros.vehiculoId} onValueChange={(v) => setFiltros({...filtros, vehiculoId: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {vehiculos.map(v => (
                    <SelectItem key={v.id} value={v.id.toString()}>{v.tipo} - {v.chapa}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Responsable</Label>
              <Select value={filtros.responsableId} onValueChange={(v) => setFiltros({...filtros, responsableId: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {usuarios.map(u => (
                    <SelectItem key={u.id} value={u.id.toString()}>{u.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Estado</Label>
              <Select value={filtros.estado} onValueChange={(v) => setFiltros({...filtros, estado: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="PENDIENTE">Pendiente</SelectItem>
                  <SelectItem value="EN_CAMINO">En Camino</SelectItem>
                  <SelectItem value="ENTREGADO">Entregado</SelectItem>
                  <SelectItem value="CANCELADO">Cancelado</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Entregas Pendientes */}
      {entregasPendientes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-yellow-600" />
              Pendientes ({entregasPendientes.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {entregasPendientes.map((entrega) => (
                <Card 
                  key={entrega.id} 
                  className="card-hover cursor-pointer border-2" 
                  onClick={() => handleCardClick(entrega)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <Badge className={cn(estadoColors[entrega.estado], 'border')}>
                        PENDIENTE
                      </Badge>
                      <span className="text-sm font-mono font-bold text-muted-foreground">
                        #{entrega.venta_id.toString().padStart(6, '0')}
                      </span>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{entrega.cliente_nombre}</span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Package className="h-4 w-4" />
                        <span className="text-xs">Sin asignar</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Entregas En Camino */}
      {entregasEnCamino.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-blue-600" />
              En Camino ({entregasEnCamino.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {entregasEnCamino.map((entrega) => (
                <Card 
                  key={entrega.id} 
                  className="card-hover cursor-pointer border-2" 
                  onClick={() => handleCardClick(entrega)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <Badge className={cn(estadoColors[entrega.estado], 'border')}>
                        EN CAMINO
                      </Badge>
                      <span className="text-sm font-mono font-bold text-muted-foreground">
                        #{entrega.venta_id.toString().padStart(6, '0')}
                      </span>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{entrega.cliente_nombre}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Truck className="h-4 w-4 text-muted-foreground" />
                        <span className="text-xs">{entrega.vehiculo_chapa}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-muted-foreground" />
                        <span className="text-xs">{entrega.responsable_nombre}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Entregas Finalizadas */}
      {entregasFinalizadas.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5 text-green-600" />
              Entregados ({entregasFinalizadas.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {entregasFinalizadas.map((entrega) => (
                <Card 
                  key={entrega.id} 
                  className="cursor-pointer border-2" 
                  onClick={() => handleCardClick(entrega)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-start justify-between mb-2">
                      <Badge className={cn(estadoColors[entrega.estado], 'border text-xs')}>
                        ENTREGADO
                      </Badge>
                      <span className="text-xs font-mono font-bold text-muted-foreground">
                        #{entrega.venta_id.toString().padStart(6, '0')}
                      </span>
                    </div>
                    
                    <div className="space-y-1">
                      <p className="text-xs font-medium truncate">{entrega.cliente_nombre}</p>
                      <p className="text-xs text-muted-foreground">{entrega.responsable_nombre}</p>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {entregas.length === 0 && (
        <Card>
          <CardContent className="p-12">
            <div className="text-center">
              <Truck className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No hay entregas para mostrar</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Modal de Detalles */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Truck className="h-5 w-5" />
              Orden de Delivery #{entregaSeleccionada?.venta_id?.toString().padStart(6, '0')}
              {entregaSeleccionada && (
                <Badge className={cn(estadoColors[entregaSeleccionada.estado], 'ml-2 border')}>
                  {entregaSeleccionada.estado.replace('_', ' ')}
                </Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {loadingDetalles ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : ventaDetalles && (
            <div className="space-y-6">
              {/* Cliente Info */}
              <div className="space-y-2">
                <h3 className="font-semibold flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Cliente
                </h3>
                <div className="bg-muted/50 p-3 rounded-md space-y-1">
                  <p className="font-medium">{ventaDetalles.cliente_nombre}</p>
                  {ventaDetalles.cliente_telefono && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Phone className="h-3 w-3" />
                      <span>{ventaDetalles.cliente_telefono}</span>
                    </div>
                  )}
                  {ventaDetalles.cliente_direccion && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      <span>{ventaDetalles.cliente_direccion}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Productos */}
              <div className="space-y-2">
                <h3 className="font-semibold flex items-center gap-2">
                  <Package className="h-4 w-4" />
                  Productos
                </h3>
                <div className="border rounded-md">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="p-2 text-left">Producto</th>
                        <th className="p-2 text-center">Cant.</th>
                        <th className="p-2 text-right">Precio</th>
                        <th className="p-2 text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ventaDetalles.items?.map((item, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="p-2">{item.producto_nombre || item.materia_nombre || 'N/A'}</td>
                          <td className="p-2 text-center">{item.cantidad}</td>
                          <td className="p-2 text-right">{formatCurrency(item.precio_unitario)}</td>
                          <td className="p-2 text-right font-medium">{formatCurrency(item.total)}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="bg-muted/50 font-semibold">
                      <tr>
                        <td colSpan="3" className="p-2 text-right">Total:</td>
                        <td className="p-2 text-right">{formatCurrency(ventaDetalles.total)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Asignación de Vehículo y Responsable */}
              {entregaSeleccionada?.estado !== 'ENTREGADO' && (
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold flex items-center gap-2">
                    <Edit className="h-4 w-4" />
                    Asignación
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Vehículo</Label>
                      <Select value={vehiculoId} onValueChange={setVehiculoId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar vehículo" />
                        </SelectTrigger>
                        <SelectContent>
                          {vehiculos.map(v => (
                            <SelectItem key={v.id} value={v.id.toString()}>
                              {v.tipo} - {v.chapa}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Responsable</Label>
                      <Select value={responsableId} onValueChange={setResponsableId}>
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar responsable" />
                        </SelectTrigger>
                        <SelectContent>
                          {usuarios.map(u => (
                            <SelectItem key={u.id} value={u.id.toString()}>
                              {u.nombre} {u.apellido}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => setModalOpen(false)}>
              Cerrar
            </Button>
            {userPermisos.includes('delivery.eliminar') && (
              <Button 
                variant="destructive" 
                onClick={handleEliminarEntrega}
                className="mr-auto"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Eliminar
              </Button>
            )}
            {entregaSeleccionada?.estado === 'PENDIENTE' && (
              <Button onClick={handleAsignar}>
                Asignar y Enviar
              </Button>
            )}
            {entregaSeleccionada?.estado === 'EN_CAMINO' && (
              <>
                <Button variant="outline" onClick={handleAsignar}>
                  Actualizar Asignación
                </Button>
                <Button onClick={handleMarcarEntregado} className="bg-green-600 hover:bg-green-700">
                  Marcar como Entregado
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{accionConfirmar?.titulo}</AlertDialogTitle>
            <AlertDialogDescription>{accionConfirmar?.descripcion}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => {
              accionConfirmar?.accion();
              setConfirmDialogOpen(false);
            }}>
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default Delivery;
