import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import { FlaskConical, Plus, Loader2, Printer } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import JsBarcode from 'jsbarcode';

const Laboratorio = () => {
  const { api, empresa } = useApp();
  const [materias, setMaterias] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [printMateria, setPrintMateria] = useState(null);
  const [printDialogOpen, setPrintDialogOpen] = useState(false);
  const barcodeRef = useRef(null);
  
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    precio: ''
  });

  const fetchMaterias = async () => {
    if (!empresa?.id) return;
    try {
      const data = await api(`/materias-laboratorio?empresa_id=${empresa.id}`);
      setMaterias(data);
    } catch (e) {
      toast.error('Error al cargar materias');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaterias();
  }, [empresa?.id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.nombre || !formData.precio) {
      toast.error('Complete todos los campos requeridos');
      return;
    }
    
    setSubmitting(true);
    try {
      await api('/materias-laboratorio', {
        method: 'POST',
        body: JSON.stringify({
          ...formData,
          empresa_id: empresa.id,
          precio: parseFloat(formData.precio)
        })
      });
      
      toast.success('Materia creada exitosamente');
      setDialogOpen(false);
      setFormData({ nombre: '', descripcion: '', precio: '' });
      fetchMaterias();
    } catch (e) {
      toast.error(e.message || 'Error al crear materia');
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('es-PY', {
      style: 'currency',
      currency: 'PYG',
      minimumFractionDigits: 0
    }).format(value);
  };

  // Render barcode into SVG via callback ref (ensures DOM is ready)
  const barcodeCallbackRef = useCallback((node) => {
    barcodeRef.current = node;
    if (node && printMateria) {
      try {
        JsBarcode(node, printMateria.codigo_barra, {
          format: 'CODE39',
          width: 3,
          height: 50,
          displayValue: true,
          fontSize: 14,
          font: 'monospace',
          fontOptions: 'bold',
          margin: 4,
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
            width: 50mm;
            height: 20mm;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 0.5mm 1mm;
            font-family: 'Courier New', monospace;
          }
          .label .name {
            font-size: 6pt;
            font-weight: bold;
            text-align: center;
            line-height: 1.1;
            max-width: 48mm;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            margin-bottom: 0.3mm;
          }
          .label svg {
            max-width: 48mm;
            height: auto;
            max-height: 14mm;
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
            <DialogHeader>
              <DialogTitle>Crear Nueva Materia</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="nombre">Nombre *</Label>
                <Input
                  id="nombre"
                  value={formData.nombre}
                  onChange={(e) => setFormData({...formData, nombre: e.target.value})}
                  placeholder="Nombre de la materia"
                  data-testid="materia-nombre"
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
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5" />
            Listado de Materias
          </CardTitle>
        </CardHeader>
        <CardContent>
          {materias.length === 0 ? (
            <div className="text-center py-12">
              <FlaskConical className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No hay materias de laboratorio creadas</p>
            </div>
          ) : (
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
                  <TableRow key={materia.id} data-testid={`materia-row-${materia.id}`}>
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
                      <Badge className={cn(
                        materia.estado === 'DISPONIBLE' ? 'badge-success' : 'badge-warning'
                      )}>
                        {materia.estado}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(materia.creado_en).toLocaleDateString('es-PY')}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handlePrintBarcode(materia)}
                        title="Imprimir etiqueta de código de barras"
                      >
                        <Printer className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Barcode Print Dialog */}
      <Dialog open={printDialogOpen} onOpenChange={setPrintDialogOpen}>
        <DialogContent className="sm:max-w-md">
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
                    width: '50mm',
                    height: '20mm',
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
                    maxWidth: '48mm',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                    marginBottom: '0.3mm'
                  }}>
                    {printMateria.nombre}
                  </p>
                  <svg ref={barcodeCallbackRef} style={{ maxWidth: '48mm', maxHeight: '14mm' }} />
                </div>
              </div>

              <p className="text-xs text-muted-foreground text-center">
                Vista previa de la etiqueta (5cm × 2cm) para Epson LX-350
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
