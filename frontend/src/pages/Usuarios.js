import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
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
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Users, Plus, Loader2, Search, Edit, Trash2, Shield, Key } from 'lucide-react';
import { toast } from 'sonner';

const Usuarios = () => {
  const { api, empresa, userPermisos } = useApp();
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    nombre: '',
    apellido: '',
    telefono: ''
  });

  const fetchData = async () => {
    if (!empresa?.id) return;
    try {
      const [usuariosData, rolesData] = await Promise.all([
        api(`/usuarios?empresa_id=${empresa.id}`),
        api(`/roles?empresa_id=${empresa.id}`)
      ]);
      console.log('Usuarios recibidos:', usuariosData);
      console.log('Roles recibidos:', rolesData);
      setUsuarios(usuariosData);
      setRoles(rolesData);
    } catch (e) {
      toast.error('Error al cargar datos');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [empresa?.id]);

  const resetForm = () => {
    setFormData({
      email: '',
      password: '',
      nombre: '',
      apellido: '',
      telefono: ''
    });
    setEditingId(null);
  };

  const handleEdit = (usuario) => {
    setFormData({
      email: usuario.email,
      password: '',
      nombre: usuario.nombre,
      apellido: usuario.apellido || '',
      telefono: usuario.telefono || ''
    });
    setEditingId(usuario.id);
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.email || !formData.nombre) {
      toast.error('Email y nombre son requeridos');
      return;
    }
    
    if (!editingId && !formData.password) {
      toast.error('La contraseña es requerida para nuevos usuarios');
      return;
    }
    
    setSubmitting(true);
    try {
      if (editingId) {
        const payload = { ...formData };
        if (!payload.password) delete payload.password;
        
        await api(`/usuarios/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        toast.success('Usuario actualizado');
      } else {
        await api('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ ...formData, empresa_id: empresa.id })
        });
        toast.success('Usuario creado');
      }
      
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (e) {
      toast.error(e.message || 'Error al guardar');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('¿Desactivar este usuario?')) return;
    try {
      await api(`/usuarios/${id}`, { method: 'DELETE' });
      toast.success('Usuario desactivado');
      fetchData();
    } catch (e) {
      toast.error('Error al eliminar');
    }
  };

  const handleAsignarRol = async (usuarioId, rolId) => {
    try {
      await api(`/usuarios/${usuarioId}/roles/${rolId}`, { method: 'POST' });
      toast.success('Rol asignado');
    } catch (e) {
      toast.error('Error al asignar rol');
    }
  };

  const filteredUsuarios = usuarios.filter(u =>
    u.nombre.toLowerCase().includes(search.toLowerCase()) ||
    u.email.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="usuarios-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Usuarios y Perfiles</h1>
          <p className="text-muted-foreground">Gestión de accesos y permisos</p>
        </div>
        {userPermisos.includes('usuarios.gestionar') && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="crear-usuario-btn">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Usuario
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Usuario</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  disabled={!!editingId}
                />
              </div>
              <div>
                <Label>Contraseña {editingId ? '(dejar vacío para mantener)' : '*'}</Label>
                <Input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  placeholder={editingId ? '••••••••' : ''}
                />
              </div>
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
              </div>
              <div>
                <Label>Teléfono</Label>
                <Input
                  value={formData.telefono}
                  onChange={(e) => setFormData({...formData, telefono: e.target.value})}
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

      {/* Roles Available */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Roles Disponibles
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {roles.map((rol) => (
              <Badge key={rol.id} variant="secondary" className="text-sm py-1 px-3">
                {rol.nombre}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Usuarios ({filteredUsuarios.length})
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
                <TableHead>Usuario</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Teléfono</TableHead>
                <TableHead>Asignar Rol</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="w-20">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredUsuarios.map((usuario) => (
                <TableRow key={usuario.id}>
                  <TableCell>
                    <p className="font-medium">{usuario.nombre} {usuario.apellido}</p>
                  </TableCell>
                  <TableCell className="text-sm">{usuario.email}</TableCell>
                  <TableCell>{usuario.telefono || '-'}</TableCell>
                  <TableCell>
                    {userPermisos.includes('usuarios.gestionar') ? (
                      <Select 
                        value={usuario.rol_id?.toString() || ""} 
                        onValueChange={(v) => handleAsignarRol(usuario.id, parseInt(v))}
                      >
                        <SelectTrigger className="w-40">
                          <SelectValue placeholder="Sin asignar" />
                        </SelectTrigger>
                        <SelectContent>
                          {roles.map(r => (
                            <SelectItem key={r.id} value={r.id.toString()}>{r.nombre}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        {roles.find(r => r.id === usuario.rol_id)?.nombre || 'Sin asignar'}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge className={usuario.activo ? "badge-success" : "badge-warning"}>
                      {usuario.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {userPermisos.includes('usuarios.gestionar') && (
                        <>
                          <Button variant="ghost" size="icon" onClick={() => handleEdit(usuario)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(usuario.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </>
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

export default Usuarios;
