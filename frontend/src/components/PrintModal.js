import React, { useState, useRef, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Label } from '../components/ui/label';
import { Loader2, Printer, Receipt, FileText, Send } from 'lucide-react';
import { toast } from 'sonner';

// Boleta Print Template
const BoletaPrint = React.forwardRef(({ data }, ref) => {
  if (!data) return null;
  
  return (
    <div ref={ref} className="print-document boleta-print" style={{ 
      fontFamily: 'Arial, sans-serif',
      fontSize: '12px',
      width: '80mm',
      padding: '10px',
      backgroundColor: 'white',
      color: 'black'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '10px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0' }}>LuzBrill</h1>
        <p style={{ margin: '2px 0', fontSize: '10px' }}>{data.empresa?.telefono || '061 572516 573408'}</p>
        <p style={{ margin: '2px 0', fontSize: '10px' }}>0983 628249 0973 598415</p>
      </div>
      
      <div style={{ textAlign: 'right', marginBottom: '10px' }}>
        <span style={{ fontWeight: 'bold' }}>NOTA NRO: </span>
        <span>{data.numero}</span>
      </div>
      
      <div style={{ borderTop: '1px dashed black', borderBottom: '1px dashed black', padding: '5px 0', marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Razon Social:</span>
          <span>{data.cliente?.nombre || 'OCACIONAL'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Dirección:</span>
          <span>{data.cliente?.direccion || '0'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Telefono:</span>
          <span>{data.cliente?.telefono || '0'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Ruc:</span>
          <span>{data.cliente?.ruc || '0'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Fecha de Venta:</span>
          <span>{data.fecha}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Tipo Comprob:</span>
          <span>{data.tipo_pago}</span>
        </div>
      </div>
      
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '10px' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid black' }}>
            <th style={{ textAlign: 'left', fontSize: '10px', padding: '2px' }}>Codigo</th>
            <th style={{ textAlign: 'center', fontSize: '10px', padding: '2px' }}>Cant.</th>
            <th style={{ textAlign: 'left', fontSize: '10px', padding: '2px' }}>Descripcion</th>
            <th style={{ textAlign: 'center', fontSize: '10px', padding: '2px' }}>IVA</th>
            <th style={{ textAlign: 'right', fontSize: '10px', padding: '2px' }}>Precio</th>
            <th style={{ textAlign: 'right', fontSize: '10px', padding: '2px' }}>Total</th>
          </tr>
        </thead>
        <tbody>
          {data.items?.map((item, idx) => (
            <tr key={idx}>
              <td style={{ fontSize: '9px', padding: '2px' }}>{item.codigo}</td>
              <td style={{ textAlign: 'center', fontSize: '9px', padding: '2px' }}>{item.cantidad?.toFixed(2)}</td>
              <td style={{ fontSize: '9px', padding: '2px' }}>{item.descripcion}</td>
              <td style={{ textAlign: 'center', fontSize: '9px', padding: '2px' }}>{item.iva}</td>
              <td style={{ textAlign: 'right', fontSize: '9px', padding: '2px' }}>{item.precio?.toLocaleString('es-PY')}</td>
              <td style={{ textAlign: 'right', fontSize: '9px', padding: '2px' }}>{item.total?.toLocaleString('es-PY')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      <div style={{ borderTop: '1px dashed black', paddingTop: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
          <span>Subtotal:</span>
          <span>{data.subtotal_sin_descuento?.toLocaleString('es-PY')}</span>
        </div>
        {data.descuento > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px', color: '#059669' }}>
            <span>Descuento ({data.descuento_porcentaje}%):</span>
            <span>-{data.descuento?.toLocaleString('es-PY')}</span>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
          <span>En Letras:</span>
          <span style={{ fontSize: '10px', textTransform: 'lowercase' }}>{data.total_letras}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '14px' }}>
          <span>Total a Pagar:</span>
          <span>{data.total?.toLocaleString('es-PY')}</span>
        </div>
      </div>
      
      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <p style={{ margin: '0 0 5px 0' }}>________________________</p>
        <p style={{ margin: '0', fontSize: '10px' }}>Firma Cliente</p>
        <p style={{ margin: '15px 0 0 0', fontSize: '9px', fontStyle: 'italic' }}>
          Favor Conferir Su Mercaderia !!! No Aceptamos Reclamos Posteriores.
        </p>
      </div>
    </div>
  );
});

// Factura Print Template  
const FacturaPrint = React.forwardRef(({ data }, ref) => {
  if (!data) return null;
  
  return (
    <div ref={ref} className="print-document factura-print" style={{ 
      fontFamily: 'Arial, sans-serif',
      fontSize: '12px',
      width: '210mm',
      padding: '20px',
      backgroundColor: 'white',
      color: 'black'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: '0' }}>{data.empresa?.nombre || 'Luz Brill S.A.'}</h1>
          <p style={{ margin: '2px 0' }}>RUC: {data.empresa?.ruc}</p>
          <p style={{ margin: '2px 0' }}>{data.empresa?.direccion}</p>
          <p style={{ margin: '2px 0' }}>Tel: {data.empresa?.telefono}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '18px', fontWeight: 'bold' }}>FACTURA</p>
          <p style={{ fontSize: '16px' }}>N° {data.numero}</p>
        </div>
      </div>
      
      <div style={{ display: 'flex', gap: '20px', marginBottom: '15px' }}>
        <div>
          <span>Ciudad del Este, </span>
          <span>{data.fecha}</span>
        </div>
        <div>
          <span>Condición: </span>
          <strong>{data.condicion}</strong>
        </div>
      </div>
      
      <div style={{ border: '1px solid black', padding: '10px', marginBottom: '15px' }}>
        <div style={{ display: 'flex', gap: '20px', marginBottom: '5px' }}>
          <span><strong>Cliente:</strong> {data.cliente?.nombre}</span>
          <span><strong>RUC:</strong> {data.cliente?.ruc}</span>
        </div>
        <div>
          <span><strong>Dirección:</strong> {data.cliente?.direccion || '-'}</span>
        </div>
      </div>
      
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '15px' }}>
        <thead>
          <tr style={{ backgroundColor: '#f0f0f0' }}>
            <th style={{ border: '1px solid black', padding: '5px', textAlign: 'center' }}>Cant.</th>
            <th style={{ border: '1px solid black', padding: '5px', textAlign: 'left' }}>Descripción</th>
            <th style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>P. Unitario</th>
            <th style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>Exenta</th>
            <th style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>IVA 5%</th>
            <th style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>IVA 10%</th>
          </tr>
        </thead>
        <tbody>
          {data.items?.map((item, idx) => (
            <tr key={idx}>
              <td style={{ border: '1px solid black', padding: '5px', textAlign: 'center' }}>{item.cantidad}</td>
              <td style={{ border: '1px solid black', padding: '5px' }}>{item.descripcion}</td>
              <td style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>{item.precio_unitario?.toLocaleString('es-PY')}</td>
              <td style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>{item.exenta || 0}</td>
              <td style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>{item.iva_5 || 0}</td>
              <td style={{ border: '1px solid black', padding: '5px', textAlign: 'right' }}>{item.iva_10?.toLocaleString('es-PY')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ maxWidth: '60%' }}>
          <p><strong>Total en letras:</strong></p>
          <p style={{ textTransform: 'lowercase', fontStyle: 'italic' }}>{data.total_letras}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <table style={{ marginLeft: 'auto' }}>
            <tbody>
              <tr>
                <td style={{ paddingRight: '20px' }}>Subtotal Exenta:</td>
                <td style={{ textAlign: 'right' }}>{data.subtotal_exenta?.toLocaleString('es-PY') || 0}</td>
              </tr>
              <tr>
                <td style={{ paddingRight: '20px' }}>Subtotal IVA 5%:</td>
                <td style={{ textAlign: 'right' }}>{data.subtotal_iva_5?.toLocaleString('es-PY') || 0}</td>
              </tr>
              <tr>
                <td style={{ paddingRight: '20px' }}>Subtotal IVA 10%:</td>
                <td style={{ textAlign: 'right' }}>{data.subtotal_iva_10?.toLocaleString('es-PY')}</td>
              </tr>
              {data.descuento > 0 && (
                <tr style={{ color: '#059669' }}>
                  <td style={{ paddingRight: '20px' }}>Descuento ({data.descuento_porcentaje}%):</td>
                  <td style={{ textAlign: 'right' }}>-{data.descuento?.toLocaleString('es-PY')}</td>
                </tr>
              )}
              <tr>
                <td style={{ paddingRight: '20px' }}>IVA 10%:</td>
                <td style={{ textAlign: 'right' }}>{data.iva_10?.toLocaleString('es-PY')}</td>
              </tr>
              <tr style={{ fontWeight: 'bold', fontSize: '14px' }}>
                <td style={{ paddingRight: '20px', borderTop: '2px solid black', paddingTop: '5px' }}>TOTAL:</td>
                <td style={{ textAlign: 'right', borderTop: '2px solid black', paddingTop: '5px' }}>Gs. {data.total?.toLocaleString('es-PY')}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '50px' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: '0 0 5px 0' }}>________________________</p>
          <p style={{ margin: '0' }}>Firma Vendedor</p>
        </div>
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: '0 0 5px 0' }}>________________________</p>
          <p style={{ margin: '0' }}>Firma Cliente</p>
        </div>
      </div>
    </div>
  );
});

const PrintModal = ({ open, onOpenChange, ventaId, onPrintComplete }) => {
  const { api } = useApp();
  const [printBoleta, setPrintBoleta] = useState(true);
  const [printFactura, setPrintFactura] = useState(false);
  const [loading, setLoading] = useState(false);
  const [boletaData, setBoletaData] = useState(null);
  const [facturaData, setFacturaData] = useState(null);
  const [error, setError] = useState(null);
  
  const boletaRef = useRef(null);
  const facturaRef = useRef(null);

  const fetchPrintData = async () => {
    if (!ventaId) return;
    setLoading(true);
    setError(null);
    
    try {
      const promises = [];
      if (printBoleta) promises.push(api(`/ventas/${ventaId}/boleta`).then(d => setBoletaData(d)));
      if (printFactura) promises.push(api(`/ventas/${ventaId}/factura`).then(d => setFacturaData(d)));
      await Promise.all(promises);
    } catch (e) {
      setError(e.message);
      toast.error(e.message || 'Error al cargar datos de impresión');
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = useCallback(async () => {
    if (!printBoleta && !printFactura) {
      toast.error('Seleccione al menos un documento');
      return;
    }
    
    await fetchPrintData();
    
    // Use a small delay to ensure data is loaded
    setTimeout(() => {
      const printContent = [];
      
      if (printBoleta && boletaRef.current) {
        printContent.push(boletaRef.current.innerHTML);
      }
      if (printFactura && facturaRef.current) {
        printContent.push(facturaRef.current.innerHTML);
      }
      
      if (printContent.length > 0) {
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(`
            <html>
              <head>
                <title>Imprimir - Venta #${ventaId}</title>
                <style>
                  body { margin: 0; padding: 20px; }
                  @media print {
                    .page-break { page-break-after: always; }
                  }
                </style>
              </head>
              <body>
                ${printContent.join('<div class="page-break"></div>')}
              </body>
            </html>
          `);
          printWindow.document.close();
          printWindow.print();
          printWindow.close();
          
          toast.success('Documento(s) enviado(s) a impresión');
          onOpenChange(false);
          if (onPrintComplete) onPrintComplete();
        }
      }
    }, 500);
  }, [printBoleta, printFactura, ventaId, onOpenChange, onPrintComplete]);

  const handleSendWhatsApp = useCallback(async () => {
    if (!printBoleta && !printFactura) {
      toast.error('Seleccione al menos un documento');
      return;
    }
    
    // Load data if not already loaded
    if (!boletaData && !facturaData) {
      await fetchPrintData();
    }
    
    // Get data from whichever document is selected
    const data = printBoleta ? boletaData : facturaData;
    
    if (!data) {
      toast.error('Error al cargar datos de venta');
      return;
    }
    
    // Check if client has phone number
    const telefono = data.cliente?.telefono;
    if (!telefono) {
      toast.error('El cliente no tiene número de teléfono registrado');
      return;
    }
    
    // Clean phone number (remove spaces, dashes, parentheses)
    const cleanPhone = telefono.replace(/[\s\-\(\)]/g, '');
    
    // Format phone for WhatsApp (Paraguay code +595)
    let whatsappNumber = cleanPhone;
    if (!whatsappNumber.startsWith('+')) {
      if (whatsappNumber.startsWith('0')) {
        whatsappNumber = '595' + whatsappNumber.substring(1);
      } else if (!whatsappNumber.startsWith('595')) {
        whatsappNumber = '595' + whatsappNumber;
      }
    }
    
    // Generate message
    const docType = printBoleta ? 'Boleta' : 'Factura';
    const message = `
🧾 *${docType} - ${data.empresa?.nombre || 'Luz Brill'}*

📋 *Número:* ${data.numero}
👤 *Cliente:* ${data.cliente?.nombre || 'Cliente'}
📅 *Fecha:* ${data.fecha}
💰 *Total:* Gs. ${data.total?.toLocaleString('es-PY')}

Gracias por su compra! 🙏

_Este es un comprobante de venta generado automáticamente._
    `.trim();
    
    // Open WhatsApp
    const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
    window.open(whatsappUrl, '_blank');
    
    toast.success('Abriendo WhatsApp...');
  }, [printBoleta, printFactura, boletaData, facturaData]);

  // Fetch data when modal opens
  React.useEffect(() => {
    if (open && ventaId) {
      fetchPrintData();
    }
  }, [open, ventaId]);

  // Reset state when modal closes
  React.useEffect(() => {
    if (!open) {
      setBoletaData(null);
      setFacturaData(null);
      setError(null);
      setPrintBoleta(true);
      setPrintFactura(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Printer className="h-5 w-5" />
            Imprimir Documento
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <p className="text-muted-foreground text-sm">
            Seleccione qué documento(s) desea imprimir para la venta #{ventaId}
          </p>
          
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              {error}
            </div>
          )}
          
          <div className="space-y-3">
            <div className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-secondary transition-colors">
              <Checkbox 
                id="boleta" 
                checked={printBoleta} 
                onCheckedChange={setPrintBoleta}
              />
              <div className="flex-1">
                <Label htmlFor="boleta" className="flex items-center gap-2 cursor-pointer">
                  <Receipt className="h-4 w-4" />
                  Boleta
                </Label>
                <p className="text-xs text-muted-foreground">
                  Documento simple para clientes sin RUC
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 p-3 border rounded-lg hover:bg-secondary transition-colors">
              <Checkbox 
                id="factura" 
                checked={printFactura} 
                onCheckedChange={setPrintFactura}
              />
              <div className="flex-1">
                <Label htmlFor="factura" className="flex items-center gap-2 cursor-pointer">
                  <FileText className="h-4 w-4" />
                  Factura
                </Label>
                <p className="text-xs text-muted-foreground">
                  Documento fiscal con desglose de IVA (requiere RUC)
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSendWhatsApp}
              variant="outline"
              disabled={loading || (!printBoleta && !printFactura)}
              className="bg-green-50 text-green-700 hover:bg-green-100 hover:text-green-800 border-green-200"
            >
              <Send className="mr-2 h-4 w-4" />
              WhatsApp
            </Button>
            <Button 
              onClick={handlePrint} 
              disabled={loading || (!printBoleta && !printFactura)}
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              <Printer className="mr-2 h-4 w-4" />
              Imprimir
            </Button>
          </div>
        </div>
      </DialogContent>
      
      {/* Hidden print containers */}
      <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
        <BoletaPrint ref={boletaRef} data={boletaData} />
        <FacturaPrint ref={facturaRef} data={facturaData} />
      </div>
    </Dialog>
  );
};

export default PrintModal;
