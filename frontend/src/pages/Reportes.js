import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { DatePicker } from '../components/ui/date-picker';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '../components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover';
import { 
  FileText, Download, Loader2, Package, Users, Building2, 
  DollarSign, Calendar, Search, X, Check
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const Reportes = () => {
  const { empresa, API_URL, token, api } = useApp();
  const [loading, setLoading] = useState({});
  const [clientes, setClientes] = useState([]);
  const [clientesLoading, setClientesLoading] = useState(true);
  
  // Filters for Ventas report
  const [ventasFechaDesde, setVentasFechaDesde] = useState(
    new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0]
  );
  const [ventasFechaHasta, setVentasFechaHasta] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [ventasTipoPago, setVentasTipoPago] = useState('TODOS');
  const [ventasEstado, setVentasEstado] = useState('CONFIRMADA');
  const [ventasClienteId, setVentasClienteId] = useState(null);
  const [ventasClienteSearch, setVentasClienteSearch] = useState('');
  const [clientePopoverOpen, setClientePopoverOpen] = useState(false);
  
  // Filters for Stock report
  const [stockFechaDesde, setStockFechaDesde] = useState('');
  const [stockFechaHasta, setStockFechaHasta] = useState('');
  const [stockSoloAlertas, setStockSoloAlertas] = useState('NO');
  
  // Filters for Deudas Proveedores
  const [deudasFechaDesde, setDeudasFechaDesde] = useState('');
  const [deudasFechaHasta, setDeudasFechaHasta] = useState('');
  const [deudasEstado, setDeudasEstado] = useState('PENDIENTE');
  
  // Filters for Créditos Clientes
  const [creditosFechaDesde, setCreditosFechaDesde] = useState('');
  const [creditosFechaHasta, setCreditosFechaHasta] = useState('');
  const [creditosEstado, setCreditosEstado] = useState('PENDIENTE');

  // Load clientes
  useEffect(() => {
    const fetchClientes = async () => {
      if (!empresa?.id) return;
      try {
        const data = await api(`/clientes?empresa_id=${empresa.id}`);
        setClientes(data);
      } catch (e) {
        console.error('Error loading clientes:', e);
      } finally {
        setClientesLoading(false);
      }
    };
    fetchClientes();
  }, [empresa?.id, api]);

  // Get selected cliente
  const selectedCliente = ventasClienteId ? clientes.find(c => c.id === ventasClienteId) : null;

  // Filter clientes by search
  const filteredClientes = clientes.filter(c => {
    const searchLower = ventasClienteSearch.toLowerCase();
    return (
      c.nombre.toLowerCase().includes(searchLower) ||
      (c.apellido && c.apellido.toLowerCase().includes(searchLower)) ||
      c.id.toString() === ventasClienteSearch ||
      (c.ruc && c.ruc.toLowerCase().includes(searchLower))
    );
  });

  const downloadReport = async (tipo, params = {}) => {
    if (!empresa?.id) {
      toast.error('No se ha seleccionado una empresa');
      return;
    }
    
    setLoading({ ...loading, [tipo]: true });
    
    try {
      let url = `${API_URL}/reportes/${tipo}?empresa_id=${empresa.id}`;
      
      // Add extra params
      Object.entries(params).forEach(([key, value]) => {
        if (value) url += `&${key}=${value}`;
      });
      
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) {
        // Try to get error message from response
        let errorMessage = 'Error al generar reporte';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          // If response is not JSON, use status text
          if (response.status === 404) {
            errorMessage = 'No se encontraron datos para este reporte';
          } else if (response.status === 403) {
            errorMessage = 'No tiene permisos para generar este reporte';
          } else if (response.status === 500) {
            errorMessage = 'Error en el servidor al generar el reporte. Contacte al administrador.';
          } else {
            errorMessage = `Error ${response.status}: ${response.statusText}`;
          }
        }
        throw new Error(errorMessage);
      }
      
      const blob = await response.blob();
      
      // Verify we got a PDF
      if (!blob.type.includes('pdf')) {
        throw new Error('El servidor no devolvió un archivo PDF válido');
      }
      
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      // Get filename from Content-Disposition header or create one
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `reporte_${tipo}_${new Date().toISOString().split('T')[0]}.pdf`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) filename = match[1];
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success('Reporte descargado exitosamente');
    } catch (e) {
      console.error('Error downloading report:', e);
      toast.error(e.message || 'Error al descargar reporte. Verifique su conexión e inténtelo nuevamente.');
    } finally {
      setLoading({ ...loading, [tipo]: false });
    }
  };

  const reportes = [
    {
      id: 'ventas',
      titulo: 'Reporte de Ventas',
      descripcion: 'Listado de ventas confirmadas por rango de fechas',
      icon: DollarSign,
      color: 'text-green-500',
      bgColor: 'bg-green-50 dark:bg-green-950',
      filters: [
        {
          type: 'dateRange',
          fromState: ventasFechaDesde,
          toState: ventasFechaHasta,
          fromSetter: setVentasFechaDesde,
          toSetter: setVentasFechaHasta
        },
        {
          type: 'select',
          label: 'Tipo de Venta',
          state: ventasTipoPago,
          setter: setVentasTipoPago,
          options: [
            { value: 'TODOS', label: 'Todas las ventas' },
            { value: 'CONTADO', label: 'Contado (Efectivo/Tarjeta/Transferencia/Cheque)' },
            { value: 'CREDITO', label: 'Crédito' }
          ]
        },
        {
          type: 'select',
          label: 'Estado',
          state: ventasEstado,
          setter: setVentasEstado,
          options: [
            { value: 'TODOS', label: 'Todos los estados' },
            { value: 'CONFIRMADA', label: 'Solo Confirmadas' },
            { value: 'ANULADA', label: 'Solo Anuladas' }
          ]
        },
        {
          type: 'clientSearch',
          label: 'Cliente (Opcional)',
          clienteId: ventasClienteId,
          setClienteId: setVentasClienteId
        }
      ],
      getParams: () => ({
        fecha_desde: ventasFechaDesde,
        fecha_hasta: ventasFechaHasta,
        tipo_pago: ventasTipoPago !== 'TODOS' ? ventasTipoPago : undefined,
        estado: ventasEstado !== 'TODOS' ? ventasEstado : undefined,
        cliente_id: ventasClienteId || undefined
      })
    },
    {
      id: 'stock',
      titulo: 'Reporte de Stock',
      descripcion: 'Estado actual del inventario con alertas de stock bajo',
      icon: Package,
      color: 'text-blue-500',
      bgColor: 'bg-blue-50 dark:bg-blue-950',
      filters: [
        {
          type: 'dateRange',
          label: 'Movimientos desde',
          fromState: stockFechaDesde,
          toState: stockFechaHasta,
          fromSetter: setStockFechaDesde,
          toSetter: setStockFechaHasta,
          optional: true
        },
        {
          type: 'select',
          label: 'Filtrar por',
          state: stockSoloAlertas,
          setter: setStockSoloAlertas,
          options: [
            { value: 'NO', label: 'Todos los productos' },
            { value: 'SI', label: 'Solo con stock bajo' }
          ]
        }
      ],
      getParams: () => ({
        fecha_desde: stockFechaDesde || undefined,
        fecha_hasta: stockFechaHasta || undefined,
        solo_alertas: stockSoloAlertas === 'SI' ? 'true' : undefined
      })
    },
    {
      id: 'deudas-proveedores',
      titulo: 'Deudas a Proveedores',
      descripcion: 'Listado de deudas pendientes con proveedores',
      icon: Building2,
      color: 'text-orange-500',
      bgColor: 'bg-orange-50 dark:bg-orange-950',
      filters: [
        {
          type: 'dateRange',
          label: 'Fecha de emisión',
          fromState: deudasFechaDesde,
          toState: deudasFechaHasta,
          fromSetter: setDeudasFechaDesde,
          toSetter: setDeudasFechaHasta,
          optional: true
        },
        {
          type: 'select',
          label: 'Estado',
          state: deudasEstado,
          setter: setDeudasEstado,
          options: [
            { value: 'TODOS', label: 'Todos los estados' },
            { value: 'PENDIENTE', label: 'Solo Pendientes' },
            { value: 'PAGADO', label: 'Solo Pagadas' }
          ]
        }
      ],
      getParams: () => ({
        fecha_desde: deudasFechaDesde || undefined,
        fecha_hasta: deudasFechaHasta || undefined,
        estado: deudasEstado !== 'TODOS' ? deudasEstado : undefined
      })
    },
    {
      id: 'creditos-clientes',
      titulo: 'Créditos de Clientes',
      descripcion: 'Listado de créditos pendientes de cobro',
      icon: Users,
      color: 'text-purple-500',
      bgColor: 'bg-purple-50 dark:bg-purple-950',
      filters: [
        {
          type: 'dateRange',
          label: 'Fecha de venta',
          fromState: creditosFechaDesde,
          toState: creditosFechaHasta,
          fromSetter: setCreditosFechaDesde,
          toSetter: setCreditosFechaHasta,
          optional: true
        },
        {
          type: 'select',
          label: 'Estado',
          state: creditosEstado,
          setter: setCreditosEstado,
          options: [
            { value: 'TODOS', label: 'Todos los estados' },
            { value: 'PENDIENTE', label: 'Solo Pendientes' },
            { value: 'PAGADO', label: 'Solo Pagados' }
          ]
        }
      ],
      getParams: () => ({
        fecha_desde: creditosFechaDesde || undefined,
        fecha_hasta: creditosFechaHasta || undefined,
        estado: creditosEstado !== 'TODOS' ? creditosEstado : undefined
      })
    }
  ];

  return (
    <div className="space-y-6" data-testid="reportes-page">
      <div>
        <h1 className="text-2xl font-bold">Reportes</h1>
        <p className="text-muted-foreground">Genera y descarga reportes en formato PDF</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reportes.map((reporte) => {
          const Icon = reporte.icon;
          return (
            <Card key={reporte.id} className="overflow-hidden">
              <CardHeader className={`${reporte.bgColor}`}>
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-background ${reporte.color}`}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{reporte.titulo}</CardTitle>
                    <CardDescription>{reporte.descripcion}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-4">
                {reporte.filters && (
                  <div className="space-y-3 mb-4">
                    {reporte.filters.map((filter, idx) => {
                      if (filter.type === 'dateRange') {
                        return (
                          <div key={idx}>
                            {filter.label && (
                              <Label className="text-xs mb-2 block">
                                {filter.label} {filter.optional && '(Opcional)'}
                              </Label>
                            )}
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <Label className="text-xs mb-1 block">Desde</Label>
                                <DatePicker
                                  date={filter.fromState}
                                  onDateChange={filter.fromSetter}
                                  placeholder="Desde"
                                  className="w-full text-sm"
                                />
                              </div>
                              <div>
                                <Label className="text-xs mb-1 block">Hasta</Label>
                                <DatePicker
                                  date={filter.toState}
                                  onDateChange={filter.toSetter}
                                  placeholder="Hasta"
                                  className="w-full text-sm"
                                />
                              </div>
                            </div>
                          </div>
                        );
                      }
                      
                      if (filter.type === 'select') {
                        return (
                          <div key={idx}>
                            <Label className="text-xs mb-1 block">{filter.label}</Label>
                            <Select value={filter.state} onValueChange={filter.setter}>
                              <SelectTrigger className="text-sm">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {filter.options.map((opt) => (
                                  <SelectItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        );
                      }

                      if (filter.type === 'clientSearch') {
                        return (
                          <div key={idx}>
                            <Label className="text-xs mb-1 block">{filter.label}</Label>
                            {selectedCliente ? (
                              <div className="flex items-center justify-between p-2 bg-secondary rounded-md text-sm">
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium truncate">
                                    {selectedCliente.nombre} {selectedCliente.apellido || ''}
                                  </p>
                                  <p className="text-xs text-muted-foreground truncate">
                                    ID: {selectedCliente.id} | RUC: {selectedCliente.ruc || 'N/A'}
                                  </p>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 ml-2"
                                  onClick={() => {
                                    filter.setClienteId(null);
                                    setVentasClienteSearch('');
                                  }}
                                >
                                  <X className="h-3 w-3" />
                                </Button>
                              </div>
                            ) : (
                              <Popover open={clientePopoverOpen} onOpenChange={setClientePopoverOpen}>
                                <PopoverTrigger asChild>
                                  <Button
                                    variant="outline"
                                    role="combobox"
                                    className="w-full justify-start text-sm h-9"
                                  >
                                    <Search className="mr-2 h-3 w-3" />
                                    Buscar por ID o nombre...
                                  </Button>
                                </PopoverTrigger>
                                <PopoverContent className="w-[300px] p-0" align="start">
                                  <Command>
                                    <CommandInput
                                      placeholder="ID, nombre o RUC..."
                                      value={ventasClienteSearch}
                                      onValueChange={setVentasClienteSearch}
                                    />
                                    <CommandEmpty>
                                      {clientesLoading ? 'Cargando...' : 'No se encontraron clientes'}
                                    </CommandEmpty>
                                    <CommandGroup className="max-h-64 overflow-auto">
                                      {filteredClientes.slice(0, 50).map((cliente) => (
                                        <CommandItem
                                          key={cliente.id}
                                          value={cliente.id.toString()}
                                          onSelect={() => {
                                            filter.setClienteId(cliente.id);
                                            setClientePopoverOpen(false);
                                            setVentasClienteSearch('');
                                          }}
                                          className="text-sm"
                                        >
                                          <Check
                                            className={cn(
                                              'mr-2 h-3 w-3',
                                              filter.clienteId === cliente.id ? 'opacity-100' : 'opacity-0'
                                            )}
                                          />
                                          <div className="flex-1 min-w-0">
                                            <p className="font-medium truncate">
                                              {cliente.nombre} {cliente.apellido || ''}
                                            </p>
                                            <p className="text-xs text-muted-foreground truncate">
                                              ID: {cliente.id} | RUC: {cliente.ruc || 'N/A'}
                                            </p>
                                          </div>
                                        </CommandItem>
                                      ))}
                                    </CommandGroup>
                                  </Command>
                                </PopoverContent>
                              </Popover>
                            )}
                          </div>
                        );
                      }
                      
                      return null;
                    })}
                  </div>
                )}
                
                <Button
                  className="w-full"
                  onClick={() => downloadReport(reporte.id, reporte.getParams())}
                  disabled={loading[reporte.id]}
                >
                  {loading[reporte.id] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generando...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Descargar PDF
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default Reportes;
