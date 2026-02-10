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
      fontFamily: 'Courier New, monospace', // Fuente monoespaciada para matriz de puntos
      fontSize: '12px',
      width: '240mm', // Papel continuo 24cm
      height: '140mm', // Altura papel boleta
      padding: '8mm 10mm', // Márgenes para matriz de puntos
      margin: '0',
      backgroundColor: 'white',
      color: 'black',
      lineHeight: '1.4'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '8px' }}>
        <h1 style={{ fontSize: '22px', fontWeight: 'bold', margin: '0', letterSpacing: '2px', textDecoration: 'underline' }}>LuzBrill</h1>
        <p style={{ margin: '3px 0', fontSize: '11px', fontWeight: 'bold' }}>{data.empresa?.telefono || '061 572516 573408'}</p>
        <p style={{ margin: '2px 0', fontSize: '11px', fontWeight: 'bold' }}>0983 628249 0973 598415</p>
      </div>
      
      <div style={{ textAlign: 'right', marginBottom: '8px', fontSize: '13px' }}>
        <span style={{ fontWeight: 'bold' }}>NOTA NRO: </span>
        <span style={{ fontWeight: 'bold' }}>{data.numero}</span>
      </div>
      
      <div style={{ borderTop: '2px solid black', borderBottom: '2px solid black', padding: '6px 0', marginBottom: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '3px 0' }}>
          <span style={{ fontWeight: 'bold' }}>Razon Social:</span>
          <span style={{ textAlign: 'right', fontWeight: 'bold' }}>{data.cliente?.nombre || 'OCACIONAL'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '3px 0' }}>
          <span style={{ fontWeight: 'bold' }}>Dirección:</span>
          <span style={{ textAlign: 'right' }}>{data.cliente?.direccion || '0'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '3px 0' }}>
          <span style={{ fontWeight: 'bold' }}>Telefono:</span>
          <span>{data.cliente?.telefono || '0'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '3px 0' }}>
          <span style={{ fontWeight: 'bold' }}>Ruc:</span>
          <span>{data.cliente?.ruc || '0'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '3px 0' }}>
          <span style={{ fontWeight: 'bold' }}>Fecha de Venta:</span>
          <span>{data.fecha}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', margin: '3px 0' }}>
          <span style={{ fontWeight: 'bold' }}>Tipo Comprob:</span>
          <span>{data.tipo_pago}</span>
        </div>
      </div>
      
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '8px' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid black', borderTop: '2px solid black' }}>
            <th style={{ textAlign: 'left', fontSize: '10px', padding: '4px', fontWeight: 'bold' }}>Cod</th>
            <th style={{ textAlign: 'center', fontSize: '10px', padding: '4px', fontWeight: 'bold' }}>Cant</th>
            <th style={{ textAlign: 'left', fontSize: '10px', padding: '4px', fontWeight: 'bold' }}>Descripción</th>
            <th style={{ textAlign: 'center', fontSize: '10px', padding: '4px', fontWeight: 'bold' }}>IVA</th>
            <th style={{ textAlign: 'right', fontSize: '10px', padding: '4px', fontWeight: 'bold' }}>Precio</th>
            <th style={{ textAlign: 'right', fontSize: '10px', padding: '4px', fontWeight: 'bold' }}>Total</th>
          </tr>
        </thead>
        <tbody>
          {data.items?.map((item, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #ccc' }}>
              <td style={{ fontSize: '10px', padding: '3px 4px' }}>{item.codigo}</td>
              <td style={{ textAlign: 'center', fontSize: '10px', padding: '3px 4px' }}>{item.cantidad?.toFixed(2)}</td>
              <td style={{ fontSize: '10px', padding: '3px 4px' }}>{item.descripcion}</td>
              <td style={{ textAlign: 'center', fontSize: '10px', padding: '3px 4px' }}>{item.iva}</td>
              <td style={{ textAlign: 'right', fontSize: '10px', padding: '3px 4px', fontWeight: 'bold' }}>{item.precio?.toLocaleString('es-PY')}</td>
              <td style={{ textAlign: 'right', fontSize: '10px', padding: '3px 4px', fontWeight: 'bold' }}>{item.total?.toLocaleString('es-PY')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      <div style={{ borderTop: '2px solid black', paddingTop: '6px', marginTop: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
          <span style={{ fontWeight: 'bold' }}>Subtotal:</span>
          <span style={{ fontWeight: 'bold' }}>{data.subtotal_sin_descuento?.toLocaleString('es-PY')}</span>
        </div>
        {data.descuento > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
            <span style={{ fontWeight: 'bold' }}>Descuento ({data.descuento_porcentaje}%):</span>
            <span style={{ fontWeight: 'bold' }}>-{data.descuento?.toLocaleString('es-PY')}</span>
          </div>
        )}
        <div style={{ marginBottom: '6px', fontSize: '10px', borderTop: '1px solid black', paddingTop: '4px' }}>
          <span style={{ fontWeight: 'bold' }}>En Letras: </span>
          <span style={{ textTransform: 'uppercase', fontWeight: 'bold' }}>{data.total_letras}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '14px', marginTop: '5px', borderTop: '3px double black', paddingTop: '6px' }}>
          <span>TOTAL A PAGAR:</span>
          <span>Gs. {data.total?.toLocaleString('es-PY')}</span>
        </div>
      </div>
      
      <div style={{ marginTop: '12px', textAlign: 'center' }}>
        <p style={{ margin: '0 0 4px 0', fontSize: '12px' }}>________________________________</p>
        <p style={{ margin: '0', fontSize: '11px', fontWeight: 'bold' }}>Firma Cliente</p>
        <p style={{ margin: '10px 0 0 0', fontSize: '9px', fontStyle: 'italic', fontWeight: 'bold' }}>
          Favor Conferir Su Mercaderia !!! No Aceptamos Reclamos Posteriores.
        </p>
      </div>
    </div>
  );
});

// Factura Print Template (Papel pre-impreso 240mm ancho)
const FacturaPrint = React.forwardRef(({ data }, ref) => {
  if (!data) return null;
  
  return (
    <div ref={ref} className="print-document factura-print" style={{ 
      fontFamily: 'Courier New, monospace', // Fuente monoespaciada para matriz de puntos
      fontSize: '12px',
      width: '240mm', // Papel continuo pre-impreso 24cm
      minHeight: '200mm', // Altura mínima, se ajusta al contenido
      padding: '10mm 12mm', // Márgenes para matriz de puntos
      backgroundColor: 'white',
      color: 'black',
      lineHeight: '1.4',
      boxSizing: 'border-box'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '15px' }}>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: 'bold', margin: '0', letterSpacing: '2px', textDecoration: 'underline' }}>{data.empresa?.nombre || 'Luz Brill S.A.'}</h1>
          <p style={{ margin: '3px 0', fontSize: '12px', fontWeight: 'bold' }}>RUC: {data.empresa?.ruc}</p>
          <p style={{ margin: '2px 0', fontSize: '12px', fontWeight: 'bold' }}>{data.empresa?.direccion}</p>
          <p style={{ margin: '2px 0', fontSize: '12px', fontWeight: 'bold' }}>Tel: {data.empresa?.telefono}</p>
        </div>
        <div style={{ textAlign: 'right', border: '3px double black', padding: '10px 20px' }}>
          <p style={{ fontSize: '18px', fontWeight: 'bold', margin: '0', letterSpacing: '1px' }}>FACTURA</p>
          <p style={{ fontSize: '16px', margin: '5px 0 0 0', fontWeight: 'bold' }}>N° {data.numero}</p>
        </div>
      </div>
      
      <div style={{ display: 'flex', gap: '30px', marginBottom: '12px', fontSize: '12px' }}>
        <div>
          <span style={{ fontWeight: 'bold' }}>Ciudad del Este, </span>
          <span style={{ fontWeight: 'bold' }}>{data.fecha}</span>
        </div>
        <div>
          <span style={{ fontWeight: 'bold' }}>Condición: </span>
          <strong>{data.condicion}</strong>
        </div>
      </div>
      
      <div style={{ border: '2px solid black', padding: '10px', marginBottom: '12px' }}>
        <div style={{ display: 'flex', gap: '30px', marginBottom: '5px', fontSize: '12px' }}>
          <span><strong>Cliente:</strong> {data.cliente?.nombre}</span>
          <span><strong>RUC:</strong> {data.cliente?.ruc}</span>
        </div>
        <div style={{ fontSize: '12px' }}>
          <span><strong>Dirección:</strong> {data.cliente?.direccion || '-'}</span>
        </div>
      </div>
      
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '12px' }}>
        <thead>
          <tr style={{ borderTop: '2px solid black', borderBottom: '2px solid black' }}>
            <th style={{ padding: '6px', textAlign: 'center', fontSize: '11px', fontWeight: 'bold' }}>Cant.</th>
            <th style={{ padding: '6px', textAlign: 'left', fontSize: '11px', fontWeight: 'bold' }}>Descripción</th>
            <th style={{ padding: '6px', textAlign: 'right', fontSize: '11px', fontWeight: 'bold' }}>P. Unitario</th>
            <th style={{ padding: '6px', textAlign: 'right', fontSize: '11px', fontWeight: 'bold' }}>Exenta</th>
            <th style={{ padding: '6px', textAlign: 'right', fontSize: '11px', fontWeight: 'bold' }}>IVA 5%</th>
            <th style={{ padding: '6px', textAlign: 'right', fontSize: '11px', fontWeight: 'bold' }}>IVA 10%</th>
          </tr>
        </thead>
        <tbody>
          {data.items?.map((item, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid #999' }}>
              <td style={{ padding: '5px', textAlign: 'center', fontSize: '11px' }}>{item.cantidad}</td>
              <td style={{ padding: '5px', fontSize: '11px' }}>{item.descripcion}</td>
              <td style={{ padding: '5px', textAlign: 'right', fontSize: '11px', fontWeight: 'bold' }}>{item.precio_unitario?.toLocaleString('es-PY')}</td>
              <td style={{ padding: '5px', textAlign: 'right', fontSize: '11px' }}>{item.exenta || 0}</td>
              <td style={{ padding: '5px', textAlign: 'right', fontSize: '11px' }}>{item.iva_5 || 0}</td>
              <td style={{ padding: '5px', textAlign: 'right', fontSize: '11px', fontWeight: 'bold' }}>{item.iva_10?.toLocaleString('es-PY')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px' }}>
        <div style={{ maxWidth: '50%' }}>
          <p style={{ margin: '0 0 4px 0', fontSize: '12px', fontWeight: 'bold' }}>Total en letras:</p>
          <p style={{ margin: '0', fontSize: '11px', textTransform: 'uppercase', fontWeight: 'bold' }}>{data.total_letras}</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <table style={{ marginLeft: 'auto', fontSize: '12px' }}>
            <tbody>
              <tr>
                <td style={{ paddingRight: '20px', paddingBottom: '4px', fontWeight: 'bold' }}>Subtotal Exenta:</td>
                <td style={{ textAlign: 'right', paddingBottom: '4px', fontWeight: 'bold' }}>{data.subtotal_exenta?.toLocaleString('es-PY') || 0}</td>
              </tr>
              <tr>
                <td style={{ paddingRight: '20px', paddingBottom: '4px', fontWeight: 'bold' }}>Subtotal IVA 5%:</td>
                <td style={{ textAlign: 'right', paddingBottom: '4px', fontWeight: 'bold' }}>{data.subtotal_iva_5?.toLocaleString('es-PY') || 0}</td>
              </tr>
              <tr>
                <td style={{ paddingRight: '20px', paddingBottom: '4px', fontWeight: 'bold' }}>Subtotal IVA 10%:</td>
                <td style={{ textAlign: 'right', paddingBottom: '4px', fontWeight: 'bold' }}>{data.subtotal_iva_10?.toLocaleString('es-PY')}</td>
              </tr>
              {data.descuento > 0 && (
                <tr>
                  <td style={{ paddingRight: '20px', paddingBottom: '4px', fontWeight: 'bold' }}>Descuento ({data.descuento_porcentaje}%):</td>
                  <td style={{ textAlign: 'right', paddingBottom: '4px', fontWeight: 'bold' }}>-{data.descuento?.toLocaleString('es-PY')}</td>
                </tr>
              )}
              <tr>
                <td style={{ paddingRight: '20px', paddingBottom: '4px', fontWeight: 'bold' }}>IVA 10%:</td>
                <td style={{ textAlign: 'right', paddingBottom: '4px', fontWeight: 'bold' }}>{data.iva_10?.toLocaleString('es-PY')}</td>
              </tr>
              <tr style={{ fontWeight: 'bold', fontSize: '14px' }}>
                <td style={{ paddingRight: '20px', borderTop: '3px double black', paddingTop: '6px' }}>TOTAL:</td>
                <td style={{ textAlign: 'right', borderTop: '3px double black', paddingTop: '6px' }}>Gs. {data.total?.toLocaleString('es-PY')}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20mm' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: '0 0 5px 0', fontSize: '12px', fontWeight: 'bold' }}>________________________________</p>
          <p style={{ margin: '0', fontSize: '11px', fontWeight: 'bold' }}>Firma Vendedor</p>
        </div>
        <div style={{ textAlign: 'center' }}>
          <p style={{ margin: '0 0 5px 0', fontSize: '12px', fontWeight: 'bold' }}>________________________________</p>
          <p style={{ margin: '0', fontSize: '11px', fontWeight: 'bold' }}>Firma Cliente</p>
        </div>
      </div>
    </div>
  );
});

const PrintModal = ({ open, onOpenChange, ventaId, ventaEstado, onPrintComplete }) => {
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
                <meta charset="UTF-8">
                <style>
                  * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                  }
                  
                  body { 
                    margin: 0; 
                    padding: 0; 
                    background: white;
                  }
                  
                  /* Estilos para impresora matriz de puntos Epson LX-350 */
                  .boleta-print {
                    margin: 0;
                    page-break-after: always;
                  }
                  
                  .factura-print {
                    margin: 0;
                    page-break-after: always;
                  }
                  
                  @media print {
                    @page {
                      size: 240mm auto; /* Papel continuo 240mm de ancho, altura automática */
                      margin: 0; /* Sin márgenes, los controlamos desde el documento */
                    }
                    
                    body {
                      margin: 0;
                      padding: 0;
                      -webkit-print-color-adjust: exact;
                      print-color-adjust: exact;
                    }
                    
                    .page-break { 
                      page-break-after: always;
                      break-after: page;
                    }
                    
                    /* Para boletas - papel continuo 240mm x 140mm */
                    .boleta-print {
                      width: 240mm;
                      height: 140mm;
                      margin: 0;
                      page-break-after: always;
                    }
                    
                    /* Para facturas - papel continuo pre-impreso 240mm */
                    .factura-print {
                      width: 240mm;
                      min-height: 200mm;
                      margin: 0;
                      page-break-after: always;
                    }
                    
                    /* Evitar cortes de página indeseados */
                    table, tr, td, th {
                      page-break-inside: avoid;
                    }
                    
                    /* Mejor contraste para matriz de puntos */
                    strong, b, .bold {
                      font-weight: 900 !important;
                    }
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
    
    setLoading(true);
    
    try {
      // Determinar tipo de documento
      const tipoDocumento = printBoleta ? 'BOLETA' : 'FACTURA';
      
      // Llamar al backend para generar enlace
      const response = await api(`/ventas/${ventaId}/generar-enlace?tipo_documento=${tipoDocumento}`, {
        method: 'POST'
      });
      
      if (!response.url) {
        throw new Error('No se pudo generar el enlace');
      }
      
      // Mostrar si es un enlace reutilizado o nuevo
      if (response.ya_existia) {
        toast.info('Reutilizando enlace existente', { duration: 2000 });
      } else {
        toast.success('Documento PDF generado', { duration: 2000 });
      }
      
      // Load data if not already loaded para obtener info del cliente
      if (!boletaData && !facturaData) {
        await fetchPrintData();
      }
      
      // Get data from whichever document is selected
      const data = printBoleta ? boletaData : facturaData;
      
      if (!data) {
        toast.error('Error al cargar datos de venta');
        setLoading(false);
        return;
      }
      
      // Check if client has phone number
      const telefono = data.cliente?.telefono;
      if (!telefono) {
        toast.error('El cliente no tiene número de teléfono registrado');
        setLoading(false);
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
      
      // Generate message with download link
      const docType = printBoleta ? 'Boleta' : 'Factura';
      const expirationDate = new Date(response.fecha_expiracion).toLocaleDateString('es-PY');
      
      // Format items list
      let itemsText = '';
      if (data.items && data.items.length > 0) {
        itemsText = '\n*PRODUCTOS:*\n';
        itemsText += '━━━━━━━━━━━━━━━━━━━━━━\n';
        data.items.forEach((item, idx) => {
          itemsText += `${idx + 1}. *${item.descripcion}*\n`;
          itemsText += `   Cant: ${item.cantidad?.toFixed(2)} | Precio: Gs. ${item.precio?.toLocaleString('es-PY')}\n`;
          itemsText += `   Subtotal: Gs. ${item.total?.toLocaleString('es-PY')}\n`;
        });
        itemsText += '━━━━━━━━━━━━━━━━━━━━━━\n';
      }
      
      const message = `
🧾 *${docType} - ${data.empresa?.nombre || 'Luz Brill'}*

📋 *Número:* ${data.numero}
👤 *Cliente:* ${data.cliente?.nombre || 'Cliente'}
📅 *Fecha:* ${data.fecha}
🏠 *Dirección:* ${data.cliente?.direccion || 'N/A'}
📞 *Teléfono:* ${data.cliente?.telefono || 'N/A'}
📝 *RUC:* ${data.cliente?.ruc || 'N/A'}
💳 *Tipo Pago:* ${data.tipo_pago}
${itemsText}
💵 *Subtotal:* Gs. ${data.subtotal_sin_descuento?.toLocaleString('es-PY')}${data.descuento > 0 ? `
🎁 *Descuento (${data.descuento_porcentaje}%):* -Gs. ${data.descuento?.toLocaleString('es-PY')}` : ''}
💰 *TOTAL A PAGAR:* Gs. ${data.total?.toLocaleString('es-PY')}

📄 *Descargar documento PDF:*
${response.url}

_Enlace válido hasta el ${expirationDate}_

Gracias por su compra! 🙏
      `.trim();
      
      // Open WhatsApp
      const whatsappUrl = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
      window.open(whatsappUrl, '_blank');
      
      if (response.ya_existia) {
        toast.success('Enlace reenviado por WhatsApp');
      } else {
        toast.success('PDF generado y enviado por WhatsApp');
      }
      
    } catch (error) {
      console.error('Error generating document link:', error);
      toast.error(error.message || 'Error al generar enlace de documento');
    } finally {
      setLoading(false);
    }
  }, [printBoleta, printFactura, ventaId, boletaData, facturaData, api, fetchPrintData]);

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
          
          {ventaEstado === 'CONFIRMADA' && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800">
              <p className="font-medium mb-1">📱 WhatsApp - Enlace inteligente:</p>
              <p className="mb-1">• Se genera un PDF único al presionar el botón</p>
              <p className="mb-1">• El cliente puede descargar el documento por 30 días</p>
              <p>• Si vuelves a enviar, se reutiliza el mismo enlace (sin duplicados)</p>
            </div>
          )}
          
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            {ventaEstado === 'CONFIRMADA' && (
              <Button 
                onClick={handleSendWhatsApp}
                variant="outline"
                disabled={loading || (!printBoleta && !printFactura)}
                className="bg-green-50 text-green-700 hover:bg-green-100 hover:text-green-800 border-green-200"
                title="Enviar resumen por WhatsApp (solo texto)"
              >
                <Send className="mr-2 h-4 w-4" />
                WhatsApp
              </Button>
            )}
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
