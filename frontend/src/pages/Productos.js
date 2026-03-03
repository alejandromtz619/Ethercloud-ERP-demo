import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';

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
import { Package, Plus, Loader2, Search, Edit, Trash2, Upload, Expand, X, Check, ChevronDown } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '../components/ui/command';
import { toast } from 'sonner';

const Productos = () => {
  const { api, empresa, userPermisos } = useApp();
  const [productos, setProductos] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [marcas, setMarcas] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [imageDialogOpen, setImageDialogOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState('');
  const [filterMarca, setFilterMarca] = useState('');
  const [filterCategoria, setFilterCategoria] = useState('');
  const [marcaOpen, setMarcaOpen] = useState(false);
  const [categoriaOpen, setCategoriaOpen] = useState(false);
  const [proveedorOpen, setProveedorOpen] = useState(false);
  
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    codigo_barra: '',
    precio_venta: '',
    precio_costo: '',
    fecha_vencimiento: '',
    categoria_id: '',
    marca_id: '',
    proveedor_id: '',
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
      // fetch proveedores separately (may be empty)
      let proveedoresData = [];
      try {
        proveedoresData = await api(`/proveedores?empresa_id=${empresa.id}`);
      } catch (err) {
        proveedoresData = [];
      }
      setProveedores(proveedoresData);
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
      precio_costo: '',
      fecha_vencimiento: '',
      categoria_id: '',
      marca_id: '',
      proveedor_id: '',
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
      precio_costo: producto.precio_costo?.toString() || '',
      fecha_vencimiento: producto.fecha_vencimiento || '',
      categoria_id: producto.categoria_id?.toString() || '',
      marca_id: producto.marca_id?.toString() || '',
      proveedor_id: producto.proveedor_id?.toString() || '',
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
        precio_costo: formData.precio_costo ? parseFloat(formData.precio_costo) : 0,
        categoria_id: formData.categoria_id ? parseInt(formData.categoria_id) : null,
        marca_id: formData.marca_id ? parseInt(formData.marca_id) : null,
        proveedor_id: formData.proveedor_id ? parseInt(formData.proveedor_id) : null,
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

  const filteredProductos = productos.filter(p => {
    const matchesSearch =
      p.nombre.toLowerCase().includes(search.toLowerCase()) ||
      p.codigo_barra?.toLowerCase().includes(search.toLowerCase());
    const matchesMarca = !filterMarca ||
      (p.marca_nombre || '').toLowerCase().includes(filterMarca.toLowerCase());
    const matchesCategoria = !filterCategoria ||
      (p.categoria_nombre || '').toLowerCase().includes(filterCategoria.toLowerCase());
    return matchesSearch && matchesMarca && matchesCategoria;
  });

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
        {userPermisos.includes('productos.crear') && (
          <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="crear-producto-btn">
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Producto
              </Button>
            </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogDescription className="hidden">Formulario para crear o editar un producto</DialogDescription>
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
                  <Label>Precio de Costo</Label>
                  <Input
                    type="number"
                    value={formData.precio_costo}
                    onChange={(e) => setFormData({...formData, precio_costo: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Categoría</Label>
                  <Popover open={categoriaOpen} onOpenChange={setCategoriaOpen}>
                    <PopoverTrigger asChild>
                      <button
                        type="button"
                        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      >
                        <span className={formData.categoria_id ? '' : 'text-muted-foreground'}>
                          {formData.categoria_id
                            ? categorias.find(c => c.id.toString() === formData.categoria_id)?.nombre
                            : 'Seleccionar'}
                        </span>
                        <ChevronDown className="h-4 w-4 opacity-50" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent className="w-64 p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Buscar categoría..." />
                        <CommandList>
                          <CommandEmpty>Sin resultados</CommandEmpty>
                          <CommandGroup>
                            <CommandItem
                              value="__none__"
                              onSelect={() => { setFormData({...formData, categoria_id: ''}); setCategoriaOpen(false); }}
                            >
                              <span className="text-muted-foreground italic">Sin categoría</span>
                            </CommandItem>
                            {categorias.map(c => (
                              <CommandItem
                                key={c.id}
                                value={c.nombre}
                                onSelect={() => { setFormData({...formData, categoria_id: c.id.toString()}); setCategoriaOpen(false); }}
                              >
                                <Check className={`mr-2 h-4 w-4 ${formData.categoria_id === c.id.toString() ? 'opacity-100' : 'opacity-0'}`} />
                                {c.nombre}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <Label>Marca</Label>
                  <Popover open={marcaOpen} onOpenChange={setMarcaOpen}>
                    <PopoverTrigger asChild>
                      <button
                        type="button"
                        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      >
                        <span className={formData.marca_id ? '' : 'text-muted-foreground'}>
                          {formData.marca_id
                            ? marcas.find(m => m.id.toString() === formData.marca_id)?.nombre
                            : 'Seleccionar'}
                        </span>
                        <ChevronDown className="h-4 w-4 opacity-50" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent className="w-64 p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Buscar marca..." />
                        <CommandList>
                          <CommandEmpty>Sin resultados</CommandEmpty>
                          <CommandGroup>
                            <CommandItem
                              value="__none__"
                              onSelect={() => { setFormData({...formData, marca_id: ''}); setMarcaOpen(false); }}
                            >
                              <span className="text-muted-foreground italic">Sin marca</span>
                            </CommandItem>
                            {marcas.map(m => (
                              <CommandItem
                                key={m.id}
                                value={m.nombre}
                                onSelect={() => { setFormData({...formData, marca_id: m.id.toString()}); setMarcaOpen(false); }}
                              >
                                <Check className={`mr-2 h-4 w-4 ${formData.marca_id === m.id.toString() ? 'opacity-100' : 'opacity-0'}`} />
                                {m.nombre}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <Label>Proveedor</Label>
                  <Popover open={proveedorOpen} onOpenChange={setProveedorOpen}>
                    <PopoverTrigger asChild>
                      <button
                        type="button"
                        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                      >
                        <span className={formData.proveedor_id ? '' : 'text-muted-foreground'}>
                          {formData.proveedor_id
                            ? proveedores.find(p => p.id.toString() === formData.proveedor_id)?.nombre
                            : 'Seleccionar'}
                        </span>
                        <ChevronDown className="h-4 w-4 opacity-50" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent className="w-64 p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Buscar proveedor..." />
                        <CommandList>
                          <CommandEmpty>Sin resultados</CommandEmpty>
                          <CommandGroup>
                            <CommandItem
                              value="__none__"
                              onSelect={() => { setFormData({...formData, proveedor_id: ''}); setProveedorOpen(false); }}
                            >
                              <span className="text-muted-foreground italic">Sin proveedor</span>
                            </CommandItem>
                            {proveedores.map(p => (
                              <CommandItem
                                key={p.id}
                                value={p.nombre}
                                onSelect={() => { setFormData({...formData, proveedor_id: p.id.toString()}); setProveedorOpen(false); }}
                              >
                                <Check className={`mr-2 h-4 w-4 ${formData.proveedor_id === p.id.toString() ? 'opacity-100' : 'opacity-0'}`} />
                                {p.nombre}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
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
        )}
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3">
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
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground font-medium">Filtros:</span>
              <div className="relative">
                <Input
                  placeholder="Marca..."
                  className="pl-3 pr-7 h-8 w-40 text-sm"
                  value={filterMarca}
                  onChange={(e) => setFilterMarca(e.target.value)}
                />
                {filterMarca && (
                  <button
                    onClick={() => setFilterMarca('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
              <div className="relative">
                <Input
                  placeholder="Categoría..."
                  className="pl-3 pr-7 h-8 w-40 text-sm"
                  value={filterCategoria}
                  onChange={(e) => setFilterCategoria(e.target.value)}
                />
                {filterCategoria && (
                  <button
                    onClick={() => setFilterCategoria('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
              {(filterMarca || filterCategoria) && (
                <button
                  onClick={() => { setFilterMarca(''); setFilterCategoria(''); }}
                  className="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1"
                >
                  <X className="h-3 w-3" /> Limpiar filtros
                </button>
              )}
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
                <TableHead>Precio Costo</TableHead>
                <TableHead>Precio Venta</TableHead>
                <TableHead>Ganancia</TableHead>
                <TableHead>Proveedor</TableHead>
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
                  <TableCell className="font-mono-data">{formatCurrency(producto.precio_costo || 0)}</TableCell>
                  <TableCell className="font-mono-data">{formatCurrency(producto.precio_venta)}</TableCell>
                  <TableCell className="font-mono">
                    {(() => {
                      const costo = Number(producto.precio_costo || 0);
                      const venta = Number(producto.precio_venta || 0);
                      const gan = venta - costo;
                      const porc = costo > 0 ? Math.round((gan / costo) * 100) : null;
                      return (
                        <div className="flex flex-col">
                          <span>{formatCurrency(gan)}</span>
                          {porc !== null ? <span className="text-xs text-muted-foreground">{porc}%</span> : <span className="text-xs text-muted-foreground">-</span>}
                        </div>
                      );
                    })()}
                  </TableCell>
                  <TableCell>{producto.proveedor_nombre || '-'}</TableCell>
                  <TableCell>
                    <Badge variant={producto.stock_total > 0 ? "secondary" : "destructive"}>
                      {producto.stock_total}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {userPermisos.includes('productos.editar') && (
                        <Button variant="ghost" size="icon" onClick={() => handleEdit(producto)}>
                          <Edit className="h-4 w-4" />
                        </Button>
                      )}
                      {userPermisos.includes('productos.eliminar') && (
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(producto.id)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
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
