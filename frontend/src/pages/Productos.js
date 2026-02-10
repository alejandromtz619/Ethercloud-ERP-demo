import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
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
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import { Package, Plus, Loader2, Search, Edit, Trash2, Upload, Expand } from 'lucide-react';
import { toast } from 'sonner';

const Productos = () => {
  const { api, empresa } = useApp();
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [imageDialogOpen, setImageDialogOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    codigo_barra: '',
    precio_venta: '',
    fecha_vencimiento: '',
    categoria_id: '',
    marca_id: '',
    imagen_url: ''
  });

  const fetchData = async () => {
    if (!empresa?.id) return;
    try {
      const [productosData, categoriasData, marcasData] = await Promise.all([
        api(`/productos?empresa_id=${empresa.id}`),
        api(`/categorias?empresa_id=${empresa.id}`),
        api(`/marcas?empresa_id=${empresa.id}`)
      ]);
      setProductos(productosData);
      setCategorias(categoriasData);
      setMarcas(marcasData);
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
      nombre: '',
      descripcion: '',
      codigo_barra: '',
      precio_venta: '',
      fecha_vencimiento: '',
      categoria_id: '',
      marca_id: '',
      imagen_url: ''
    });
    setEditingId(null);
  };

  const handleEdit = (producto) => {
    setFormData({
      nombre: producto.nombre,
      descripcion: producto.descripcion || '',
      codigo_barra: producto.codigo_barra || '',
      precio_venta: producto.precio_venta?.toString() || '',
      fecha_vencimiento: producto.fecha_vencimiento || '',
      categoria_id: producto.categoria_id?.toString() || '',
      marca_id: producto.marca_id?.toString() || '',
      imagen_url: producto.imagen_url || ''
    });
    setEditingId(producto.id);
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.nombre || !formData.precio_venta) {
      toast.error('Complete nombre y precio');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        ...formData,
        precio_venta: parseFloat(formData.precio_venta),
        categoria_id: formData.categoria_id ? parseInt(formData.categoria_id) : null,
        marca_id: formData.marca_id ? parseInt(formData.marca_id) : null,
        fecha_vencimiento: formData.fecha_vencimiento || null
      };

      if (editingId) {
        await api(`/productos/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        toast.success('Producto actualizado');
      } else {
        await api('/productos', {
          method: 'POST',
          body: JSON.stringify({ ...payload, empresa_id: empresa.id })
        });
        toast.success('Producto creado');
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
    if (!window.confirm('⚠️ ADVERTENCIA: Al eliminar este producto se eliminará PERMANENTEMENTE todo el stock asociado en todos los almacenes y el historial de movimientos.\n\n¿Está seguro de continuar?')) return;
    try {
      await api(`/productos/${id}`, { method: 'DELETE' });
      toast.success('Producto y stock eliminados correctamente');
      fetchData();
    } catch (e) {
      toast.error('Error al eliminar producto');
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PY', {
      style: 'currency',
      currency: 'PYG',
      minimumFractionDigits: 0
    }).format(value);
  };

  const filteredProductos = productos.filter(p =>
    p.nombre.toLowerCase().includes(search.toLowerCase()) ||
    p.codigo_barra?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="productos-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Productos</h1>
          <p className="text-muted-foreground">Gestión del catálogo de productos</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button data-testid="crear-producto-btn">
              <Plus className="mr-2 h-4 w-4" />
              Nuevo Producto
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>{editingId ? 'Editar' : 'Nuevo'} Producto</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Nombre *</Label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                    data-testid="producto-nombre"
                  />
                </div>
                <div className="col-span-2">
                  <Label>Descripción</Label>
                  <Textarea
                    value={formData.descripcion}
                    onChange={(e) => setFormData({...formData, descripcion: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Código de Barra</Label>
                  <Input
                    value={formData.codigo_barra}
                    onChange={(e) => setFormData({...formData, codigo_barra: e.target.value})}
                    className="font-mono"
                    data-testid="producto-codigo"
                  />
                </div>
                <div>
                  <Label>Precio de Venta *</Label>
                  <Input
                    type="number"
                    value={formData.precio_venta}
                    onChange={(e) => setFormData({...formData, precio_venta: e.target.value})}
                    data-testid="producto-precio"
                  />
                </div>
                <div>
                  <Label>Categoría</Label>
                  <Select value={formData.categoria_id} onValueChange={(v) => setFormData({...formData, categoria_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      {categorias.map(c => (
                        <SelectItem key={c.id} value={c.id.toString()}>{c.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Marca</Label>
                  <Select value={formData.marca_id} onValueChange={(v) => setFormData({...formData, marca_id: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar" />
                    </SelectTrigger>
                    <SelectContent>
                      {marcas.map(m => (
                        <SelectItem key={m.id} value={m.id.toString()}>{m.nombre}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Fecha Vencimiento</Label>
                  <Input
                    type="date"
                    value={formData.fecha_vencimiento}
                    onChange={(e) => setFormData({...formData, fecha_vencimiento: e.target.value})}
                  />
                </div>
                <div>
                  <Label>URL Imagen</Label>
                  <Input
                    value={formData.imagen_url}
                    onChange={(e) => setFormData({...formData, imagen_url: e.target.value})}
                    placeholder="https://..."
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting} data-testid="guardar-producto-btn">
                  {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  Guardar
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Catálogo ({filteredProductos.length})
            </CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar..."
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                data-testid="buscar-producto"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="table-compact">
                <TableHead className="w-16">ID</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead>Código</TableHead>
                <TableHead>Categoría</TableHead>
                <TableHead>Precio</TableHead>
                <TableHead>Stock</TableHead>
                <TableHead className="w-28">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredProductos.map((producto) => (
                <TableRow key={producto.id} data-testid={`producto-row-${producto.id}`}>
                  <TableCell className="font-mono text-sm font-bold">{producto.id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      {producto.imagen_url ? (
                        <div 
                          className="relative w-10 h-10 cursor-pointer group"
                          onClick={() => {
                            setSelectedImage(producto.imagen_url);
                            setImageDialogOpen(true);
                          }}
                        >
                          <img src={producto.imagen_url} alt="" className="w-10 h-10 rounded object-cover" />
                          <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center">
                            <Expand className="h-4 w-4 text-white" />
                          </div>
                        </div>
                      ) : (
                        <div className="w-10 h-10 rounded bg-muted flex items-center justify-center">
                          <Package className="h-5 w-5 text-muted-foreground" />
                        </div>
                      )}
                      <div>
                        <p className="font-medium">{producto.nombre}</p>
                        {producto.marca_nombre && (
                          <p className="text-xs text-muted-foreground">{producto.marca_nombre}</p>
                        )}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{producto.codigo_barra || '-'}</TableCell>
                  <TableCell>{producto.categoria_nombre || '-'}</TableCell>
                  <TableCell className="font-mono-data">{formatCurrency(producto.precio_venta)}</TableCell>
                  <TableCell>
                    <Badge variant={producto.stock_total > 0 ? "secondary" : "destructive"}>
                      {producto.stock_total}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(producto)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(producto.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Image Preview Dialog */}
      <Dialog open={imageDialogOpen} onOpenChange={setImageDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Imagen del Producto</DialogTitle>
          </DialogHeader>
          {selectedImage && (
            <img 
              src={selectedImage} 
              alt="Producto" 
              className="w-full h-auto max-h-[70vh] object-contain rounded-lg"
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Productos;
