import React, { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
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
import { FlaskConical, Plus, Loader2, Printer, Pencil, Search, Trash2, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import JsBarcode from 'jsbarcode';

const PAGE_SIZE = 50;

// Instanciados una sola vez: antes se creaba un Intl.NumberFormat por celda y render.
const currencyFormatter = new Intl.NumberFormat('es-PY', {
  style: 'currency',
  currency: 'PYG',
  minimumFractionDigits: 0
});
const dateFormatter = new Intl.DateTimeFormat('es-PY', { timeZone: 'America/Asuncion' });

const formatCurrency = (value) => currencyFormatter.format(value);

// Fila memoizada: solo recibe primitivas y callbacks estables, de modo que abrir
// un modal (o teclear en el buscador) no vuelve a renderizar la tabla entera.
const MateriaRow = memo(function MateriaRow({ materia, puedeEditar, puedeEliminar, onEdit, onPrint, onDelete }) {
  const disponible = materia.estado === 'DISPONIBLE';
  return (
    <TableRow data-testid={`materia-row-${materia.id}`}>
      <TableCell>
        <div>
          <p className="font-medium">{materia.nombre}</p>
          {materia.descripcion && (
            <p className="text-xs text-muted-foreground truncate max-w-xs">
              {materia.descripcion}
            </p>
          )}
        </div>
      </TableCell>
      <TableCell className="font-mono text-sm">{materia.codigo_barra}</TableCell>
      <TableCell className="font-mono-data">{formatCurrency(materia.precio)}</TableCell>
      <TableCell>
        <Badge className={cn(disponible ? 'badge-success' : 'badge-warning')}>
          {materia.estado}
        </Badge>
      </TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {dateFormatter.format(new Date(materia.creado_en))}
      </TableCell>
      <TableCell className="text-right">
        {disponible && puedeEditar && (
          <Button variant="ghost" size="sm" onClick={() => onEdit(materia)} title="Editar materia">
            <Pencil className="h-4 w-4" />
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onPrint(materia)}
          title="Imprimir etiqueta de código de barras"
        >
          <Printer className="h-4 w-4" />
        </Button>
        {disponible && puedeEliminar && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(materia)}
            title="Eliminar materia"
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
});

const MateriasTable = memo(function MateriasTable({ materias, puedeEditar, puedeEliminar, onEdit, onPrint, onDelete }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="table-compact">
          <TableHead>Nombre</TableHead>
          <TableHead>Código</TableHead>
          <TableHead>Precio</TableHead>
          <TableHead>Estado</TableHead>
          <TableHead>Creado</TableHead>
          <TableHead className="text-right">Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {materias.map((materia) => (
          <MateriaRow
            key={materia.id}
            materia={materia}
            puedeEditar={puedeEditar}
            puedeEliminar={puedeEliminar}
            onEdit={onEdit}
            onPrint={onPrint}
            onDelete={onDelete}
          />
        ))}
      </TableBody>
    </Table>
  );
});

const Laboratorio = () => {
  const { api, empresa, hasPermission } = useApp();
  const [materias, setMaterias] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [printMateria, setPrintMateria] = useState(null);
  const [printDialogOpen, setPrintDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editMateria, setEditMateria] = useState(null);
  const [editFormData, setEditFormData] = useState({ nombre: '', descripcion: '', precio: '' });
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterEstado, setFilterEstado] = useState('todos');
  const [sortOrder, setSortOrder] = useState('newest');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteMateria, setDeleteMateria] = useState(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const barcodeRef = useRef(null);

  const [formData, setFormData] = useState({
    cliente: '',
    pintura: '',
    descripcion: '',
    precio: ''
  });

  const puedeEditar = hasPermission('laboratorio.editar');
  const puedeEliminar = hasPermission('laboratorio.eliminar');

  // Debounce del buscador: una petición por pausa de tecleo, no por tecla.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchQuery.trim()), 350);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // Cualquier cambio de filtro vuelve a la primera página.
  useEffect(() => {
    setPage(0);
  }, [debouncedSearch, filterEstado, sortOrder]);

  const fetchMaterias = useCallback(async () => {
    if (!empresa?.id) return;
    setRefreshing(true);
    try {
      const params = new URLSearchParams({
        empresa_id: String(empresa.id),
        orden: sortOrder,
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (debouncedSearch) params.set('search', debouncedSearch);
      if (filterEstado !== 'todos') params.set('estado', filterEstado);

      const data = await api(`/materias-laboratorio?${params.toString()}`);
      setMaterias(data.items);
      setTotal(data.total);
    } catch (e) {
      toast.error('Error al cargar materias');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [api, empresa?.id, debouncedSearch, filterEstado, sortOrder, page]);

  useEffect(() => {
    fetchMaterias();
  }, [fetchMaterias]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.cliente || !formData.pintura || !formData.precio) {
      toast.error('Complete todos los campos requeridos');
      return;
    }

    const nombre = `${formData.pintura.trim()} ${formData.cliente.trim()}`;

    setSubmitting(true);
    try {
      await api('/materias-laboratorio', {
        method: 'POST',
        body: JSON.stringify({
          nombre,
          descripcion: formData.descripcion || null,
          empresa_id: empresa.id,
          precio: parseFloat(formData.precio)
        })
      });

      toast.success('Materia creada exitosamente');
      setDialogOpen(false);
      setFormData({ cliente: '', pintura: '', descripcion: '', precio: '' });
      fetchMaterias();
    } catch (e) {
      toast.error(e.message || 'Error al crear materia');
    } finally {
      setSubmitting(false);
    }
  };

  // Render barcode into SVG via callback ref (ensures DOM is ready)
  const barcodeCallbackRef = useCallback((node) => {
    barcodeRef.current = node;
    if (node && printMateria) {
      try {
        JsBarcode(node, printMateria.codigo_barra, {
          format: 'CODE128',
          width: 2,
          height: 50,
          displayValue: true,
          fontSize: 12,
          font: 'monospace',
          fontOptions: 'bold',
          margin: 3,
          textMargin: 2,
          background: '#ffffff',
          lineColor: '#000000'
        });
      } catch (err) {
        console.error('Error generating barcode:', err);
      }
    }
  }, [printMateria]);

  const handlePrintBarcode = useCallback((materia) => {
    setPrintMateria(materia);
    setPrintDialogOpen(true);
  }, []);

  const handleDeleteOpen = useCallback((materia) => {
    setDeleteMateria(materia);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = async () => {
    if (!deleteMateria) return;
    setDeleteSubmitting(true);
    try {
      await api(`/materias-laboratorio/${deleteMateria.id}`, { method: 'DELETE' });
      toast.success('Materia eliminada');
      setDeleteDialogOpen(false);
      fetchMaterias();
    } catch (e) {
      toast.error(e.message || 'Error al eliminar materia');
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const handleEditOpen = useCallback((materia) => {
    setEditMateria(materia);
    setEditFormData({ nombre: materia.nombre, descripcion: materia.descripcion || '', precio: String(materia.precio) });
    setEditDialogOpen(true);
  }, []);

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editFormData.nombre || !editFormData.precio) {
      toast.error('Complete todos los campos requeridos');
      return;
    }
    setEditSubmitting(true);
    try {
      await api(`/materias-laboratorio/${editMateria.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          nombre: editFormData.nombre,
          descripcion: editFormData.descripcion || null,
          precio: parseFloat(editFormData.precio)
        })
      });
      toast.success('Materia actualizada');
      setEditDialogOpen(false);
      fetchMaterias();
    } catch (e) {
      toast.error(e.message || 'Error al actualizar materia');
    } finally {
      setEditSubmitting(false);
    }
  };

  const executePrint = useCallback(() => {
    if (!printMateria || !barcodeRef.current) return;

    const printWindow = window.open('', '_blank', 'width=400,height=300');
    if (!printWindow) {
      toast.error('No se pudo abrir la ventana de impresión. Permita ventanas emergentes.');
      return;
    }

    // Sticker dimensions: 3.5cm wide, 2cm tall
    const svgElement = barcodeRef.current;
    const svgData = new XMLSerializer().serializeToString(svgElement);

    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Etiqueta - ${printMateria.codigo_barra}</title>
        <style>
          @page {
            size: auto;
            margin: 0;
          }
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }
          html, body {
            margin: 0;
            padding: 0;
            overflow: hidden;
          }
          .label {
            position: absolute;
            left: 0;
            top: 0;
            width: 40mm;
            height: 30mm;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1mm 1mm;
            font-family: 'Courier New', monospace;
          }
          .label .name {
            font-size: 7pt;
            font-weight: bold;
            text-align: center;
            line-height: 1.1;
            max-width: 38mm;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            margin-bottom: 1mm;
          }
          .label svg {
            max-width: 38mm;
            height: auto;
            max-height: 22mm;
          }
          @media print {
            html, body {
              margin: 0;
              padding: 0;
            }
          }
        </style>
      </head>
      <body>
        <div class="label">
          <div class="name">${printMateria.nombre}</div>
          ${svgData}
        </div>
        <script>
          window.onload = function() {
            setTimeout(function() {
              window.print();
              window.onafterprint = function() { window.close(); };
            }, 200);
          };
        </script>
      </body>
      </html>
    `);
    printWindow.document.close();
  }, [printMateria]);

  const totalPaginas = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const desde = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const hasta = Math.min(total, (page + 1) * PAGE_SIZE);
  const hayFiltros = debouncedSearch !== '' || filterEstado !== 'todos';

  const tabla = useMemo(() => (
    <MateriasTable
      materias={materias}
      puedeEditar={puedeEditar}
      puedeEliminar={puedeEliminar}
      onEdit={handleEditOpen}
      onPrint={handlePrintBarcode}
      onDelete={handleDeleteOpen}
    />
  ), [materias, puedeEditar, puedeEliminar, handleEditOpen, handlePrintBarcode, handleDeleteOpen]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="laboratorio-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Laboratorio</h1>
          <p className="text-muted-foreground">
            Crear items únicos para ventas (solo se pueden vender una vez)
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button data-testid="crear-materia-btn">
              <Plus className="mr-2 h-4 w-4" />
              Nueva Materia
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogDescription className="hidden">
              Formulario para crear una nueva materia de laboratorio
            </DialogDescription>
            <DialogHeader>
              <DialogTitle>Crear Nueva Materia</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="cliente">Cliente *</Label>
                <Input
                  id="cliente"
                  value={formData.cliente}
                  onChange={(e) => setFormData({...formData, cliente: e.target.value})}
                  placeholder="Nombre del cliente"
                  data-testid="materia-cliente"
                />
              </div>
              <div>
                <Label htmlFor="pintura">Pintura *</Label>
                <Input
                  id="pintura"
                  value={formData.pintura}
                  onChange={(e) => setFormData({...formData, pintura: e.target.value})}
                  placeholder="Ej: BLANCO PERLA 1LTS"
                  data-testid="materia-pintura"
                />
              </div>
              <div>
                <Label htmlFor="descripcion">Descripción</Label>
                <Textarea
                  id="descripcion"
                  value={formData.descripcion}
                  onChange={(e) => setFormData({...formData, descripcion: e.target.value})}
                  placeholder="Descripción detallada..."
                  data-testid="materia-descripcion"
                />
              </div>
              <div className="rounded-md bg-muted/50 p-3 text-sm text-muted-foreground">
                El código de barras se generará automáticamente al guardar.
              </div>
              <div>
                <Label htmlFor="precio">Precio de Venta (Gs.) *</Label>
                <Input
                  id="precio"
                  type="number"
                  value={formData.precio}
                  onChange={(e) => setFormData({...formData, precio: e.target.value})}
                  placeholder="0"
                  data-testid="materia-precio"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting} data-testid="guardar-materia-btn">
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Guardar
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5" />
              Listado de Materias
              {refreshing && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            </CardTitle>
            <div className="flex flex-wrap gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nombre..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 h-9 w-48"
                />
              </div>
              <Select value={filterEstado} onValueChange={setFilterEstado}>
                <SelectTrigger className="h-9 w-36">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos</SelectItem>
                  <SelectItem value="DISPONIBLE">Disponible</SelectItem>
                  <SelectItem value="VENDIDO">Vendido</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortOrder} onValueChange={setSortOrder}>
                <SelectTrigger className="h-9 w-40">
                  <SelectValue placeholder="Ordenar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newest">Más reciente</SelectItem>
                  <SelectItem value="oldest">Más antiguo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {materias.length === 0 ? (
            <div className="text-center py-12">
              {hayFiltros ? (
                <>
                  <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">Sin resultados para los filtros aplicados</p>
                </>
              ) : (
                <>
                  <FlaskConical className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No hay materias de laboratorio creadas</p>
                </>
              )}
            </div>
          ) : (
            <>
              {tabla}
              <div className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-muted-foreground">
                  Mostrando {desde}–{hasta} de {total}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0 || refreshing}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Anterior
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Página {page + 1} de {totalPaginas}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page + 1 >= totalPaginas || refreshing}
                  >
                    Siguiente
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar materia?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará permanentemente <strong>{deleteMateria?.nombre}</strong>. Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteSubmitting}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleteSubmitting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogDescription className="hidden">
            Formulario para editar una materia de laboratorio
          </DialogDescription>
          <DialogHeader>
            <DialogTitle>Editar Materia</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEditSubmit} className="space-y-4">
            <div>
              <Label htmlFor="edit-nombre">Nombre *</Label>
              <Input
                id="edit-nombre"
                value={editFormData.nombre}
                onChange={(e) => setEditFormData({...editFormData, nombre: e.target.value})}
                placeholder="Nombre de la materia"
              />
            </div>
            <div>
              <Label htmlFor="edit-descripcion">Descripción</Label>
              <Textarea
                id="edit-descripcion"
                value={editFormData.descripcion}
                onChange={(e) => setEditFormData({...editFormData, descripcion: e.target.value})}
                placeholder="Descripción detallada..."
              />
            </div>
            <div>
              <Label htmlFor="edit-precio">Precio de Venta (Gs.) *</Label>
              <Input
                id="edit-precio"
                type="number"
                value={editFormData.precio}
                onChange={(e) => setEditFormData({...editFormData, precio: e.target.value})}
                placeholder="0"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setEditDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={editSubmitting}>
                {editSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Guardar cambios
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Barcode Print Dialog */}
      <Dialog open={printDialogOpen} onOpenChange={setPrintDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogDescription className="hidden">
            Diálogo para imprimir etiquetas de código de barras
          </DialogDescription>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Printer className="h-5 w-5" />
              Imprimir Etiqueta
            </DialogTitle>
          </DialogHeader>
          {printMateria && (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                <p><strong>Materia:</strong> {printMateria.nombre}</p>
                <p><strong>Código:</strong> <span className="font-mono">{printMateria.codigo_barra}</span></p>
                <p><strong>Precio:</strong> {formatCurrency(printMateria.precio)}</p>
              </div>

              {/* Preview: simulates label 3.5cm × 2cm */}
              <div className="flex justify-center">
                <div
                  style={{
                    width: '40mm',
                    height: '30mm',
                    border: '1px dashed hsl(var(--border))',
                    borderRadius: '2px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '0.5mm 1mm',
                    backgroundColor: 'white',
                    overflow: 'hidden'
                  }}
                >
                  <p style={{
                    fontSize: '6pt',
                    fontWeight: 'bold',
                    color: 'black',
                    textAlign: 'center',
                    lineHeight: 1.1,
                    maxWidth: '38mm',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    marginBottom: '0.3mm'
                  }}>
                    {printMateria.nombre}
                  </p>
                  <svg ref={barcodeCallbackRef} style={{ maxWidth: '38mm', maxHeight: '22mm' }} />
                </div>
              </div>

              <p className="text-xs text-muted-foreground text-center">
                Vista previa de la etiqueta (4cm × 3cm) para Epson LX-350
              </p>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setPrintDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={executePrint}>
                  <Printer className="h-4 w-4 mr-2" />
                  Imprimir
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Laboratorio;
