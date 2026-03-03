import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../components/ui/tabs';
import { Shield, Plus, Loader2, Search, Edit, Trash2, Key, Users, Settings } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

// Default permissions that should exist in the system
const DEFAULT_PERMISSIONS = [
  { clave: 'ventas.crear', descripcion: 'Crear nuevas ventas' },
  { clave: 'ventas.modificar', descripcion: 'Modificar ventas existentes' },
  { clave: 'ventas.anular', descripcion: 'Anular ventas' },
  { clave: 'ventas.ver_historial', descripcion: 'Ver historial de ventas' },
  { clave: 'productos.crear', descripcion: 'Crear productos' },
  { clave: 'productos.modificar', descripcion: 'Modificar productos' },
  { clave: 'productos.eliminar', descripcion: 'Eliminar productos' },
  { clave: 'productos.modificar_precio', descripcion: 'Modificar precios de productos' },
  { clave: 'stock.ajustar', descripcion: 'Ajustar stock manualmente' },
  { clave: 'stock.traspasar', descripcion: 'Traspasar stock entre almacenes' },
  { clave: 'clientes.crear', descripcion: 'Crear clientes' },
  { clave: 'clientes.modificar', descripcion: 'Modificar clientes' },
  { clave: 'clientes.eliminar', descripcion: 'Eliminar clientes' },
  { clave: 'funcionarios.ver_salarios', descripcion: 'Ver salarios de funcionarios' },
  { clave: 'funcionarios.adelantos', descripcion: 'Registrar adelantos de salario' },
  { clave: 'reportes.ver', descripcion: 'Ver reportes del sistema' },
  { clave: 'sistema.configurar', descripcion: 'Configurar sistema' },
  { clave: 'usuarios.gestionar', descripcion: 'Gestionar usuarios y roles' },
];

const Permisos = () => {
  const { api, empresa } = useApp();
  const [roles, setRoles] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRol, setSelectedRol] = useState(null);
  const [rolPermisos, setRolPermisos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  
  // Dialog states
  const [rolDialogOpen, setRolDialogOpen] = useState(false);
  const [permisoDialogOpen, setPermisoDialogOpen] = useState(false);
  const [editingRolId, setEditingRolId] = useState(null);
  
  // Form states
  const [rolForm, setRolForm] = useState({ nombre: '', descripcion: '' });
  const [permisoForm, setPermisoForm] = useState({ clave: '', descripcion: '' });

  const fetchData = async () => {
    if (!empresa?.id) return;
    try {
      const [rolesData, permisosData, usuariosData] = await Promise.all([
        api(`/roles?empresa_id=${empresa.id}`),
        api('/permisos'),
        api(`/usuarios?empresa_id=${empresa.id}`)
      ]);
      setRoles(rolesData);
      setPermisos(permisosData);
      setUsuarios(usuariosData);
      
      // Create default permissions if none exist
      if (permisosData.length === 0) {
        await initializeDefaultPermissions();
      }
    } catch (e) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  const initializeDefaultPermissions = async () => {
    try {
      for (const perm of DEFAULT_PERMISSIONS) {
        await api('/permisos', {
          method: 'POST',
          body: JSON.stringify(perm)
        });
      }
      const newPermisos = await api('/permisos');
      setPermisos(newPermisos);
      toast.success('Permisos predeterminados creados');
    } catch (e) {
      console.error('Error creating default permissions:', e);
    }
  };

  useEffect(() => {
    fetchData();
  }, [empresa?.id]);

  const fetchRolPermisos = async (rolId) => {
    try {
      const data = await api(`/roles/${rolId}/permisos`);
      setRolPermisos(data.map(p => p.id));
    } catch (e) {
      toast.error('Error al cargar permisos del rol');
    }
  };

  const handleSelectRol = (rol) => {
    setSelectedRol(rol);
    fetchRolPermisos(rol.id);
  };

  const handleTogglePermiso = async (permisoId) => {
    if (!selectedRol) return;
    
    try {
      if (rolPermisos.includes(permisoId)) {
        await api(`/roles/${selectedRol.id}/permisos/${permisoId}`, { method: 'DELETE' });
        setRolPermisos(rolPermisos.filter(id => id !== permisoId));
        toast.success('Permiso quitado');
      } else {
        await api(`/roles/${selectedRol.id}/permisos/${permisoId}`, { method: 'POST' });
        setRolPermisos([...rolPermisos, permisoId]);
        toast.success('Permiso asignado');
      }
    } catch (e) {
      toast.error('Error al modificar permiso');
    }
  };

  const handleCreateRol = async (e) => {
    e.preventDefault();
    if (!rolForm.nombre) {
      toast.error('El nombre es requerido');
      return;
    }
    
    setSubmitting(true);
    try {
      if (editingRolId) {
        // Update existing rol - would need PUT endpoint
        toast.info('Función en desarrollo');
      } else {
        await api('/roles', {
          method: 'POST',
          body: JSON.stringify({ ...rolForm, empresa_id: empresa.id })
        });
        toast.success('Rol creado');
      }
      setRolDialogOpen(false);
      setRolForm({ nombre: '', descripcion: '' });
      setEditingRolId(null);
      fetchData();
    } catch (e) {
      toast.error('Error al guardar rol');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreatePermiso = async (e) => {
    e.preventDefault();
    if (!permisoForm.clave) {
      toast.error('La clave es requerida');
      return;
    }
    
    setSubmitting(true);
    try {
      await api('/permisos', {
        method: 'POST',
        body: JSON.stringify(permisoForm)
      });
      toast.success('Permiso creado');
      setPermisoDialogOpen(false);
      setPermisoForm({ clave: '', descripcion: '' });
      fetchData();
    } catch (e) {
      toast.error('Error al crear permiso');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="permisos-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Roles y Permisos</h1>
          <p className="text-muted-foreground">Gestión de accesos y permisos del sistema</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={rolDialogOpen} onOpenChange={setRolDialogOpen}>
            <DialogTrigger asChild>
              <Button data-testid="crear-rol-btn">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Rol
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogDescription className="hidden">Formulario para crear o editar un rol</DialogDescription>
              <DialogHeader>
                <DialogTitle>{editingRolId ? 'Editar' : 'Nuevo'} Rol</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateRol} className="space-y-4">
                <div>
                  <Label>Nombre *</Label>
                  <Input
                    value={rolForm.nombre}
                    onChange={(e) => setRolForm({...rolForm, nombre: e.target.value})}
                    placeholder="Ej: Vendedor Senior"
                  />
                </div>
                <div>
                  <Label>Descripción</Label>
                  <Input
                    value={rolForm.descripcion}
                    onChange={(e) => setRolForm({...rolForm, descripcion: e.target.value})}
                    placeholder="Descripción del rol"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setRolDialogOpen(false)}>
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
          
          <Dialog open={permisoDialogOpen} onOpenChange={setPermisoDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" data-testid="crear-permiso-btn">
                <Key className="mr-2 h-4 w-4" />
                Nuevo Permiso
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogDescription className="hidden">Formulario para crear un nuevo permiso</DialogDescription>
              <DialogHeader>
                <DialogTitle>Nuevo Permiso</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreatePermiso} className="space-y-4">
                <div>
                  <Label>Clave *</Label>
                  <Input
                    value={permisoForm.clave}
                    onChange={(e) => setPermisoForm({...permisoForm, clave: e.target.value})}
                    placeholder="Ej: ventas.descuento_especial"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Usar formato: modulo.accion
                  </p>
                </div>
                <div>
                  <Label>Descripción</Label>
                  <Input
                    value={permisoForm.descripcion}
                    onChange={(e) => setPermisoForm({...permisoForm, descripcion: e.target.value})}
                    placeholder="Descripción del permiso"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => setPermisoDialogOpen(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={submitting}>
                    {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                    Crear
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Roles List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Roles ({roles.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96">
              <div className="space-y-2">
                {roles.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No hay roles creados
                  </p>
                ) : (
                  roles.map((rol) => (
                    <div
                      key={rol.id}
                      className={cn(
                        "p-3 rounded-lg border cursor-pointer transition-colors",
                        selectedRol?.id === rol.id 
                          ? "bg-primary/10 border-primary" 
                          : "hover:bg-secondary"
                      )}
                      onClick={() => handleSelectRol(rol)}
                      data-testid={`rol-card-${rol.id}`}
                    >
                      <p className="font-medium">{rol.nombre}</p>
                      {rol.descripcion && (
                        <p className="text-xs text-muted-foreground">{rol.descripcion}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Permissions Assignment */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              {selectedRol ? `Permisos de "${selectedRol.nombre}"` : 'Seleccione un Rol'}
            </CardTitle>
            <CardDescription>
              {selectedRol 
                ? 'Marque los permisos que desea asignar a este rol' 
                : 'Haga clic en un rol para gestionar sus permisos'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedRol ? (
              <ScrollArea className="h-96">
                <div className="space-y-4">
                  {/* Group permissions by module */}
                  {Object.entries(
                    permisos.reduce((acc, perm) => {
                      const module = perm.clave.split('.')[0] || 'general';
                      if (!acc[module]) acc[module] = [];
                      acc[module].push(perm);
                      return acc;
                    }, {})
                  ).map(([module, modulePermisos]) => (
                    <div key={module}>
                      <h4 className="font-semibold capitalize mb-2 text-sm text-muted-foreground">
                        {module}
                      </h4>
                      <div className="space-y-2">
                        {modulePermisos.map((permiso) => (
                          <div
                            key={permiso.id}
                            className="flex items-center space-x-3 p-2 rounded-lg hover:bg-secondary"
                          >
                            <Checkbox
                              id={`permiso-${permiso.id}`}
                              checked={rolPermisos.includes(permiso.id)}
                              onCheckedChange={() => handleTogglePermiso(permiso.id)}
                            />
                            <div className="flex-1">
                              <Label 
                                htmlFor={`permiso-${permiso.id}`}
                                className="text-sm font-medium cursor-pointer"
                              >
                                {permiso.clave}
                              </Label>
                              {permiso.descripcion && (
                                <p className="text-xs text-muted-foreground">
                                  {permiso.descripcion}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      <Separator className="my-3" />
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="h-96 flex items-center justify-center">
                <div className="text-center">
                  <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    Seleccione un rol de la lista para gestionar sus permisos
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* All Permissions Table */}
      <Card>
        <CardHeader>
          <CardTitle>Todos los Permisos del Sistema ({permisos.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="table-compact">
                <TableHead>Clave</TableHead>
                <TableHead>Descripción</TableHead>
                <TableHead>Roles con este permiso</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {permisos.map((permiso) => (
                <TableRow key={permiso.id}>
                  <TableCell className="font-mono text-sm">{permiso.clave}</TableCell>
                  <TableCell>{permiso.descripcion || '-'}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {roles.filter(r => 
                        r.id === selectedRol?.id && rolPermisos.includes(permiso.id)
                      ).length > 0 && (
                        <Badge variant="secondary">{selectedRol?.nombre}</Badge>
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

export default Permisos;
