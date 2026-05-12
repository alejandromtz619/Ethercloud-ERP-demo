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

// Boleta Print Template - Impresora matricial Epson (papel ~190mm x 170mm)
const BoletaPrint = React.forwardRef(({ data }, ref) => {
  if (!data) return null;

  return (
    <div ref={ref} className="print-document boleta-print" style={{
      fontFamily: "'Courier New', Courier, monospace",
      fontSize: '11px',
      width: '100%',
      padding: '0',
      margin: '0',
      backgroundColor: 'white',
      color: 'black',
      lineHeight: '1.2',
      boxSizing: 'border-box'
    }}>
      {/* Encabezado */}
      <div style={{ textAlign: 'center', marginBottom: '3px' }}>
        <div style={{ fontSize: '15px', fontWeight: 'bold', letterSpacing: '3px' }}>LUZBRILL PINTURAS</div>
        <div>{data.empresa?.ruc}</div>
        <div>{data.empresa?.telefono}</div>
      </div>

      <div style={{ borderTop: '1px solid black', margin: '3px 0' }} />

      {/* Datos de la nota y cliente */}
      <div style={{ textAlign: 'right', marginBottom: '1px' }}>NOTA NRO: {data.numero}</div>
      <div>Razon Social: {data.cliente?.nombre || 'OCACIONAL'}</div>
      <div>Direccion: {data.cliente?.direccion || '-'}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Ruc: {data.cliente?.ruc || '-'}</span>
        <span>Telefono: {data.cliente?.telefono || '-'}</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Fecha: {data.fecha}</span>
        <span>Tipo Comprob: {data.tipo_pago}</span>
      </div>

      <div style={{ borderTop: '1px dashed black', margin: '3px 0' }} />

      {/* Encabezado de columnas */}
      <div style={{ display: 'flex', fontWeight: 'bold' }}>
        <span style={{ width: '7ch', textAlign: 'right', paddingRight: '1ch' }}>Cant</span>
        <span style={{ flex: 1 }}>Descripcion</span>
        <span style={{ width: '4ch', textAlign: 'center' }}>IVA</span>
        <span style={{ width: '10ch', textAlign: 'right' }}>Precio</span>
        <span style={{ width: '11ch', textAlign: 'right' }}>Total</span>
      </div>

      <div style={{ borderTop: '1px dashed black', margin: '2px 0' }} />

      {/* Filas de productos */}
      {data.items?.map((item, idx) => (
        <div key={idx} style={{ display: 'flex' }}>
          <span style={{ width: '7ch', textAlign: 'right', paddingRight: '1ch' }}>{item.cantidad?.toFixed(2)}</span>
          <span style={{ flex: 1, overflow: 'hidden', whiteSpace: 'nowrap' }}>{item.descripcion}</span>
          <span style={{ width: '4ch', textAlign: 'center' }}>{item.iva}</span>
          <span style={{ width: '10ch', textAlign: 'right' }}>{item.precio?.toLocaleString('es-PY')}</span>
          <span style={{ width: '11ch', textAlign: 'right' }}>{item.total?.toLocaleString('es-PY')}</span>
        </div>
      ))}

      <div style={{ borderTop: '1px dashed black', margin: '3px 0' }} />

      {/* Descuento (si aplica) */}
      {data.descuento > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>Descuento ({data.descuento_porcentaje}%):</span>
          <span>-{data.descuento?.toLocaleString('es-PY')}</span>
        </div>
      )}

      {/* En Letras y Total */}
      <div style={{ marginBottom: '2px' }}>En Letras: {data.total_letras}</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
        <span>Total a Pagar:</span>
        <span>Gs. {data.total?.toLocaleString('es-PY')}</span>
      </div>

      <div style={{ borderTop: '1px solid black', margin: '5px 0 4px 0' }} />

      {/* Firma */}
      <div style={{ marginTop: '8px' }}>
        <div style={{ marginBottom: '2px' }}>________________________________</div>
        <div>Firma Cliente</div>
        <div style={{ marginTop: '5px', fontSize: '9px' }}>Favor Confirmar Su Mercaderia al recibirla.</div>
        <div style={{ fontSize: '9px' }}>No Aceptamos Reclamos Posteriores.</div>
      </div>
    </div>
  );
});

// ═══════════════════════════════════════════════════════════════════════════════
// Factura Print Template - Papel PRE-IMPRESO 240mm × 200mm (Epson LX-350)
// Solo imprime DATOS sin gráficos, bordes ni cabeceras (ya están pre-impresos)
// ═══════════════════════════════════════════════════════════════════════════════
// GUÍA DE CALIBRACIÓN:
//   - Ajustar valores 'top' (mm) para mover líneas arriba/abajo
//   - Ajustar valores 'left' (mm) para mover campos izquierda/derecha
//   - Si los datos quedan muy arriba, aumentar el 'top'
//   - Si los datos quedan muy a la izquierda, aumentar el 'left'
// ═══════════════════════════════════════════════════════════════════════════════
const FacturaPrint = React.forwardRef(({ data }, ref) => {
  if (!data) return null;

  // ---------- Parsear fecha en componentes (día, mes, año) ----------
  const mesesES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
  const mesesEN = { January: 0, February: 1, March: 2, April: 3, May: 4, June: 5,
                    July: 6, August: 7, September: 8, October: 9, November: 10, December: 11 };

  let dia = '', mes = '', anio = '';

  if (data.creado_en) {
    const d = new Date(data.creado_en);
    dia = d.getDate();
    mes = mesesES[d.getMonth()];
    anio = d.getFullYear();
  } else if (data.fecha) {
    const match = data.fecha.match(/(\d+)\s+de\s+(\w+)\s+de\s+(\d+)/);
    if (match) {
      dia = parseInt(match[1]);
      const monthStr = match[2];
      anio = match[3];
      mes = mesesEN[monthStr] !== undefined ? mesesES[mesesEN[monthStr]] : monthStr;
    }
  }

  // ---------- Condición de venta ----------
  // CREDITO = marca X en Crédito; todo lo demás (EFECTIVO, TARJETA, etc.) = Contado
  const esCredito = data.condicion?.toUpperCase() === 'CREDITO';

  // ---------- Formatear números ----------
  const fmt = (n) => (n != null && n !== 0) ? Number(n).toLocaleString('es-PY') : '0';

  return (
    <div ref={ref} className="print-document factura-print" style={{
      fontFamily: 'Courier New, monospace',
      fontSize: '14px',
      fontWeight: 'bold',
      width: '240mm',
      height: '200mm',
      position: 'relative',
      backgroundColor: 'white',
      color: 'black',
      overflow: 'hidden',
      boxSizing: 'border-box',
      padding: '0',
      margin: '0',
      lineHeight: '1.2'
    }}>

      {/* ═══ LÍNEA DE FECHA + CONDICIÓN DE VENTA ═══ */}
      {/* Campos: Ciudad+día | mes | año | X Contado | X Crédito */}
      <div style={{ position: 'absolute', top: '38mm', left: '0', width: '240mm' }}>
        {/* Ciudad y día */}
        <span style={{ position: 'absolute', left: '17mm', fontSize: '14px' }}>Ciudad del Este, {dia}</span>
        {/* Mes */}
        <span style={{ position: 'absolute', left: '80mm', fontSize: '14px' }}>{mes}</span>
        {/* Año */}
        <span style={{ position: 'absolute', left: '120mm', fontSize: '14px' }}>{anio}</span>
        {/* Marca X en Contado o Crédito */}
        <span style={{ position: 'absolute', left: '183mm', fontSize: '16px', fontWeight: '900' }}>{!esCredito ? 'X' : ''}</span>
        <span style={{ position: 'absolute', left: '211mm', fontSize: '16px', fontWeight: '900' }}>{esCredito ? 'XX' : ''}</span>
      </div>

      {/* ═══ NOMBRE DEL CLIENTE + CI/RUC ═══ */}
      <div style={{ position: 'absolute', top: '45mm', left: '0', width: '240mm' }}>
        <span style={{ position: 'absolute', left: '30mm', fontSize: '14px' }}>
          {data.cliente?.nombre || 'OCACIONAL'}
        </span>
        <span style={{ position: 'absolute', left: '170mm', fontSize: '14px' }}>
          {data.cliente?.ruc || ''}
        </span>
      </div>

      {/* ═══ DIRECCIÓN + TELÉFONO ═══ */}
      <div style={{ position: 'absolute', top: '51mm', left: '0', width: '240mm' }}>
        <span style={{ position: 'absolute', left: '30mm', fontSize: '14px' }}>
          {data.cliente?.direccion || ''}
        </span>
        <span style={{ position: 'absolute', left: '180mm', fontSize: '14px' }}>
          {data.cliente?.telefono || ''}
        </span>
      </div>

      {/* ═══ TABLA DE PRODUCTOS (solo datos, sin encabezados) ═══ */}
      {/* Columnas: Cantidad | Descripción | P.Unitario | Exentas | 5% | 10% */}
      <div style={{ position: 'absolute', top: '82mm', left: '0', width: '227mm' }}>
        {data.items?.map((item, idx) => (
          <div key={idx} style={{
            position: 'relative',
            height: '5.6mm',
            fontSize: '13px',
            lineHeight: '5.6mm'
          }}>
            {/* Cantidad */}
            <span style={{ position: 'absolute', left: '17mm', width: '14mm', textAlign: 'center' }}>
              {item.es_continuacion ? '' : item.cantidad}
            </span>
            {/* Descripción */}
            <span style={{ position: 'absolute', left: '31mm', width: '80mm', textAlign: 'left', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
              {item.descripcion}
            </span>
            {/* Precio Unitario */}
            <span style={{ position: 'absolute', left: '102mm', width: '28mm', textAlign: 'right' }}>
              {item.es_continuacion ? '' : fmt(item.precio_unitario)}
            </span>
            {/* Exentas */}
            <span style={{ position: 'absolute', left: '142mm', width: '24mm', textAlign: 'right' }}>
              {item.es_continuacion ? '' : (item.exenta || 0)}
            </span>
            {/* 5% */}
            <span style={{ position: 'absolute', left: '168mm', width: '24mm', textAlign: 'right' }}>
              {item.es_continuacion ? '' : (item.iva_5 || 0)}
            </span>
            {/* 10% */}
            <span style={{ position: 'absolute', left: '194mm', width: '28mm', textAlign: 'right' }}>
              {item.es_continuacion ? '' : fmt(item.iva_10)}
            </span>
          </div>
        ))}
      </div>

      {/* ═══ SUB-TOTALES ═══ */}
      {/* Valores en las 3 últimas columnas: Exentas | 5% | 10% */}
      <div style={{ position: 'absolute', top: '150mm', left: '0', width: '227mm', fontSize: '13px' }}>
        <span style={{ position: 'absolute', left: '142mm', width: '24mm', textAlign: 'right' }}>
          {data.subtotal_exenta || 0}
        </span>
        <span style={{ position: 'absolute', left: '168mm', width: '24mm', textAlign: 'right' }}>
          {data.subtotal_iva_5 || 0}
        </span>
        <span style={{ position: 'absolute', left: '194mm', width: '28mm', textAlign: 'right' }}>
          {fmt(data.subtotal_iva_10 || data.total)}
        </span>
      </div>

      {/* ═══ TOTAL A PAGAR (letras a la izquierda, número a la derecha) ═══ */}
      <div style={{ position: 'absolute', top: '160mm', left: '0', width: '227mm' }}>
        {/* Total en letras */}
        <span style={{
          position: 'absolute', left: '25mm', fontSize: '12px',
          textTransform: 'lowercase', maxWidth: '130mm',
          overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis'
        }}>
          {data.total_letras}--
        </span>
        {/* Total numérico */}
        <span style={{ position: 'absolute', left: '194mm', width: '28mm', textAlign: 'right', fontSize: '13px' }}>
          {fmt(data.total)}
        </span>
      </div>

      {/* ═══ LIQUIDACIÓN DEL IVA ═══ */}
      {/* Campos: IVA 5% | IVA 10% | Total IVA */}
      <div style={{ position: 'absolute', top: '168mm', left: '0', width: '227mm', fontSize: '13px' }}>
        {/* Valor IVA 5% */}
        <span style={{ position: 'absolute', left: '45mm', width: '28mm', textAlign: 'right' }}>
          {data.liquidacion_iva?.iva_5 || 0}
        </span>
        {/* Valor IVA 10% */}
        <span style={{ position: 'absolute', left: '110mm', width: '28mm', textAlign: 'right' }}>
          {fmt(data.liquidacion_iva?.iva_10)}
        </span>
        {/* Total IVA */}
        <span style={{ position: 'absolute', left: '194mm', width: '28mm', textAlign: 'right' }}>
          {fmt(data.liquidacion_iva?.total_iva)}
        </span>
      </div>

    </div>
  );
});

const PrintModal = ({ open, onOpenChange, ventaId, ventaEstado, onPrintComplete }) => {
  const { api, userPermisos } = useApp();
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
                  
                  /* Estilos para impresora Epson LX-350 */
                  .boleta-print {
                    margin: 0 auto;
                    page-break-after: always;
                  }
                  
                  /* Factura: papel pre-impreso 240mm × 200mm */
                  .factura-print {
                    margin: 0;
                    padding: 0;
                    page-break-after: always;
                  }
                  
                  /* Tabla responsive - evitar overflow horizontal */
                  table {
                    width: 100% !important;
                    table-layout: fixed;
                  }
                  
                  td, th {
                    overflow: hidden;
                    text-overflow: ellipsis;
                    word-wrap: break-word;
                  }
                  
                  @media print {
                    @page {
                      size: auto;
                      margin: 15mm 8mm 10mm 8mm;
                    }

                    /* Boleta: papel continuo ~190mm x 170mm */
                    @page boleta {
                      size: 190mm 170mm;
                      margin: 5mm 5mm;
                    }

                    /* Factura pre-impresa 240mm x 200mm */
                    @page factura {
                      size: 240mm 200mm;
                      margin: 0;
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

                    .boleta-print {
                      page: boleta;
                      width: 180mm !important;
                      margin: 0 !important;
                      page-break-after: always;
                    }

                    .factura-print {
                      width: 240mm !important;
                      height: 200mm !important;
                      margin: 0 !important;
                      padding: 0 !important;
                      page-break-after: always;
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
      const expirationDate = new Date(response.fecha_expiracion).toLocaleDateString('es-PY', { timeZone: 'America/Asuncion' });
      
      const message = `
🧾 *${docType} - ${data.empresa?.nombre || 'Luz Brill'}*

📋 *Número:* ${data.numero}
📅 *Fecha:* ${data.fecha}
💰 *TOTAL:* Gs. ${data.total?.toLocaleString('es-PY')}

📄 *Ver documento completo:*
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
            
            {userPermisos.includes('ventas.imprimir_factura') && (
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
            )}
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

export { FacturaPrint };
export default PrintModal;
