import React, { useState, useRef, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { Button } from '../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { DatePickerInput } from '../components/ui/date-picker-input';
import { Loader2, Printer, Receipt, FileText, Send, CalendarDays, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';

import { useAjustesImpresion } from '../lib/ajustesImpresion';
import { useModulos } from '../lib/modulos';
import PanelFacturaElectronica from './FacturaElectronica';

// Ciudad que se imprime junto a la fecha en la factura pre-impresa: Sistema › Configuración › Documentos
// impresos. REACT_APP_CIUDAD_FACTURA queda sólo para instancias que todavía no la cargaron.
const CIUDAD_FACTURA_ANTERIOR = process.env.REACT_APP_CIUDAD_FACTURA || '';

// Formatea "YYYY-MM-DD" como "dd/MM/yyyy" sin depender de la zona horaria del navegador
const formatFechaISO = (iso) => {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
};

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
        <div style={{ fontSize: '15px', fontWeight: 'bold', letterSpacing: '3px' }}>{data.empresa?.nombre?.toUpperCase()}</div>
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
        <span>Tipo Comprob: {data.estado === 'PENDIENTE' ? 'SOLO PRESUPUESTO' : data.tipo_pago}</span>
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
        {data.estado === 'PENDIENTE' ? (
          <div style={{ marginTop: '5px', fontSize: '9px' }}>Este documento es solo una cotizacion, la venta no esta confirmada y no es valida en stock ni credito del cliente.</div>
        ) : (
          <>
            <div style={{ marginTop: '5px', fontSize: '9px' }}>Favor Confirmar Su Mercaderia al recibirla.</div>
            <div style={{ fontSize: '9px' }}>No Aceptamos Reclamos Posteriores.</div>
          </>
        )}
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
  const ajustes = useAjustesImpresion();
  if (!data) return null;
  const ciudad = ajustes.ciudad_factura || CIUDAD_FACTURA_ANTERIOR;

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
     {/* Corrimiento fino para que lo impreso caiga en los casilleros de este papel (Configuración) */}
     <div style={{ position: 'absolute', inset: 0,
                   transform: `translate(${Number(ajustes.ajuste_x_mm) || 0}mm, ${Number(ajustes.ajuste_y_mm) || 0}mm)` }}>

      {/* ═══ LÍNEA DE FECHA + CONDICIÓN DE VENTA ═══ */}
      {/* Campos: Ciudad+día | mes | año | X Contado | X Crédito */}
      <div style={{ position: 'absolute', top: '38mm', left: '0', width: '240mm' }}>
        {/* Ciudad y día */}
        <span style={{ position: 'absolute', left: '17mm', fontSize: '14px' }}>{ciudad ? `${ciudad}, ` : ''}{dia}</span>
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
    </div>
  );
});

const PrintModal = ({ open, onOpenChange, ventaId, ventaEstado, onPrintComplete }) => {
  const { api, userPermisos } = useApp();
  const modulos = useModulos();
  const [tipoDocumento, setTipoDocumento] = useState('BOLETA'); // 'BOLETA' | 'FACTURA'
  const [loading, setLoading] = useState(false);
  const [boletaData, setBoletaData] = useState(null);
  const [facturaData, setFacturaData] = useState(null);
  const [error, setError] = useState(null);
  // Fecha de impresión editable (no modifica la fecha real de la venta)
  const [fechas, setFechas] = useState(null);
  const [editandoFecha, setEditandoFecha] = useState(null); // 'BOLETA' | 'FACTURA' | null
  const [fechaTemp, setFechaTemp] = useState('');
  const [guardandoFecha, setGuardandoFecha] = useState(false);

  const boletaRef = useRef(null);
  const facturaRef = useRef(null);

  const getFechaImpresion = (tipo) => (
    tipo === 'FACTURA' ? fechas?.fecha_impresion_factura : fechas?.fecha_impresion_boleta
  );

  const fetchFechas = async () => {
    if (!ventaId) return;
    try {
      const data = await api(`/ventas/${ventaId}/fechas-impresion`);
      setFechas(data);
    } catch (e) {
      // No bloquea la impresión: solo se pierde la opción de corregir la fecha
      console.error('Error al cargar fechas de impresión', e);
    }
  };

  const abrirEditorFecha = (tipo) => {
    if (editandoFecha === tipo) {
      setEditandoFecha(null);
      return;
    }
    setFechaTemp(getFechaImpresion(tipo) || fechas?.fecha_original || '');
    setEditandoFecha(tipo);
  };

  const guardarFecha = async (tipo, fecha) => {
    setGuardandoFecha(true);
    try {
      await api(`/ventas/${ventaId}/fecha-impresion`, {
        method: 'PUT',
        body: JSON.stringify({ tipo_documento: tipo, fecha: fecha || null })
      });
      toast.success(fecha ? 'Fecha de impresión actualizada' : 'Se restauró la fecha original');
      setEditandoFecha(null);
      await fetchFechas();
      await fetchPrintData();
      onPrintComplete?.();
    } catch (e) {
      toast.error(e.message || 'Error al actualizar la fecha de impresión');
    } finally {
      setGuardandoFecha(false);
    }
  };

  const fetchPrintData = async () => {
    if (!ventaId) return;
    setLoading(true);
    setError(null);
    
    try {
      const promises = [];
      if (tipoDocumento === 'BOLETA') promises.push(api(`/ventas/${ventaId}/boleta`).then(d => setBoletaData(d)));
      else if (tipoDocumento === 'FACTURA') promises.push(api(`/ventas/${ventaId}/factura`).then(d => setFacturaData(d)));
      await Promise.all(promises);
    } catch (e) {
      setError(e.message);
      toast.error(e.message || 'Error al cargar datos de impresión');
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = useCallback(async () => {
    if (!tipoDocumento) {
      toast.error('Seleccione un documento');
      return;
    }

    await fetchPrintData();

    // Use a small delay to ensure data is loaded
    setTimeout(() => {
      const printContent = [];

      if (tipoDocumento === 'BOLETA' && boletaRef.current) {
        printContent.push(boletaRef.current.innerHTML);
      }
      if (tipoDocumento === 'FACTURA' && facturaRef.current) {
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
  }, [tipoDocumento, ventaId, onOpenChange, onPrintComplete]);

  const handleSendWhatsApp = useCallback(async () => {
    if (!tipoDocumento) {
      toast.error('Seleccione un documento');
      return;
    }

    setLoading(true);

    try {
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
      const data = tipoDocumento === 'BOLETA' ? boletaData : facturaData;
      
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
      const docType = tipoDocumento === 'BOLETA' ? 'Boleta' : 'Factura';
      const expirationDate = new Date(response.fecha_expiracion).toLocaleDateString('es-PY', { timeZone: 'America/Asuncion' });
      
      const message = `
🧾 *${docType} - ${data.empresa?.nombre || ''}*

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
  }, [tipoDocumento, ventaId, boletaData, facturaData, api, fetchPrintData]);

  // Fetch data when modal opens
  React.useEffect(() => {
    if (open && ventaId) {
      fetchPrintData();
      fetchFechas();
    }
  }, [open, ventaId]);

  // Reset state when modal closes
  React.useEffect(() => {
    if (!open) {
      setBoletaData(null);
      setFacturaData(null);
      setError(null);
      setTipoDocumento('BOLETA');
      setFechas(null);
      setEditandoFecha(null);
      setFechaTemp('');
    }
  }, [open]);

  // Botón / badge de fecha de impresión al lado de cada documento
  const renderBotonFecha = (tipo) => {
    const modificada = getFechaImpresion(tipo);
    return (
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => abrirEditorFecha(tipo)}
        title={modificada
          ? `Fecha de impresión modificada: ${formatFechaISO(modificada)} (clic para cambiar o restaurar)`
          : 'Cambiar la fecha que se imprime en este documento'}
        className={modificada
          ? 'shrink-0 h-auto py-1 px-2 text-xs font-medium bg-amber-100 text-amber-800 hover:bg-amber-200 hover:text-amber-900 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50'
          : 'shrink-0 h-auto py-1 px-2 text-xs text-muted-foreground'}
      >
        <CalendarDays className="h-3.5 w-3.5 mr-1" />
        {modificada ? formatFechaISO(modificada) : 'Fecha'}
      </Button>
    );
  };

  // Editor inline que se despliega debajo del documento seleccionado
  const renderEditorFecha = (tipo) => {
    if (editandoFecha !== tipo) return null;
    const modificada = getFechaImpresion(tipo);
    return (
      <div className="px-3 pb-3 pt-1 space-y-2 border-t bg-muted/30">
        <Label className="text-xs">Fecha a imprimir en {tipo === 'FACTURA' ? 'la factura' : 'la boleta'}</Label>
        <DatePickerInput value={fechaTemp} onChange={setFechaTemp} />
        <p className="text-xs text-muted-foreground">
          Fecha real de la venta: {formatFechaISO(fechas?.fecha_original)}
          {fechas?.hora_original ? ` ${fechas.hora_original}` : ''} — no se modifica.
          {tipo === 'BOLETA' ? ' Se conserva la hora original.' : ''}
        </p>
        <div className="flex justify-end gap-2">
          {modificada && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={guardandoFecha}
              onClick={() => guardarFecha(tipo, null)}
            >
              <RotateCcw className="h-3.5 w-3.5 mr-1" />
              Restaurar original
            </Button>
          )}
          <Button type="button" variant="outline" size="sm" onClick={() => setEditandoFecha(null)}>
            Cancelar
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={guardandoFecha || !fechaTemp}
            onClick={() => guardarFecha(tipo, fechaTemp)}
          >
            {guardandoFecha && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
            Guardar
          </Button>
        </div>
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Printer className="h-5 w-5" />
            Imprimir Documento
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <p className="text-muted-foreground text-sm">
            Seleccione qué documento desea imprimir para la venta #{ventaId}
          </p>
          
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              {error}
            </div>
          )}
          
          <div className="space-y-3">
            <div className={`border rounded-lg ${tipoDocumento === 'BOLETA' ? 'border-primary ring-1 ring-primary' : ''}`}>
              <div
                role="radio"
                aria-checked={tipoDocumento === 'BOLETA'}
                tabIndex={0}
                onClick={() => setTipoDocumento('BOLETA')}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setTipoDocumento('BOLETA')}
                className="flex items-center space-x-3 p-3 hover:bg-secondary transition-colors rounded-lg cursor-pointer"
              >
                <div className={`h-4 w-4 shrink-0 rounded-full border flex items-center justify-center ${tipoDocumento === 'BOLETA' ? 'border-primary' : 'border-muted-foreground'}`}>
                  {tipoDocumento === 'BOLETA' && <div className="h-2 w-2 rounded-full bg-primary" />}
                </div>
                <div className="flex-1">
                  <span className="flex items-center gap-2">
                    <Receipt className="h-4 w-4" />
                    Boleta
                  </span>
                  <p className="text-xs text-muted-foreground">
                    Documento simple para clientes sin RUC
                  </p>
                </div>
                {renderBotonFecha('BOLETA')}
              </div>
              {renderEditorFecha('BOLETA')}
            </div>

            {userPermisos.includes('ventas.imprimir_factura') && (
              <div className={`border rounded-lg ${tipoDocumento === 'FACTURA' ? 'border-primary ring-1 ring-primary' : ''}`}>
                <div
                  role="radio"
                  aria-checked={tipoDocumento === 'FACTURA'}
                  tabIndex={0}
                  onClick={() => setTipoDocumento('FACTURA')}
                  onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setTipoDocumento('FACTURA')}
                  className="flex items-center space-x-3 p-3 hover:bg-secondary transition-colors rounded-lg cursor-pointer"
                >
                  <div className={`h-4 w-4 shrink-0 rounded-full border flex items-center justify-center ${tipoDocumento === 'FACTURA' ? 'border-primary' : 'border-muted-foreground'}`}>
                    {tipoDocumento === 'FACTURA' && <div className="h-2 w-2 rounded-full bg-primary" />}
                  </div>
                  <div className="flex-1">
                    <span className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Factura
                    </span>
                    <p className="text-xs text-muted-foreground">
                      Documento fiscal con desglose de IVA (requiere RUC)
                    </p>
                  </div>
                  {renderBotonFecha('FACTURA')}
                </div>
                {renderEditorFecha('FACTURA')}
              </div>
            )}

            {modulos.fe && ventaEstado === 'CONFIRMADA' && (
              <div className={`border rounded-lg ${tipoDocumento === 'FE' ? 'border-primary ring-1 ring-primary' : ''}`}>
                <div
                  role="radio"
                  aria-checked={tipoDocumento === 'FE'}
                  tabIndex={0}
                  data-testid="opcion-fe"
                  onClick={() => setTipoDocumento('FE')}
                  onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setTipoDocumento('FE')}
                  className="flex items-center space-x-3 p-3 hover:bg-secondary transition-colors rounded-lg cursor-pointer"
                >
                  <div className={`h-4 w-4 shrink-0 rounded-full border flex items-center justify-center ${tipoDocumento === 'FE' ? 'border-primary' : 'border-muted-foreground'}`}>
                    {tipoDocumento === 'FE' && <div className="h-2 w-2 rounded-full bg-primary" />}
                  </div>
                  <div className="flex-1">
                    <span className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Factura electrónica
                    </span>
                    <p className="text-xs text-muted-foreground">Se envía a SIFEN; se imprime el KuDE (ticket o A4)</p>
                  </div>
                </div>
                {tipoDocumento === 'FE' && (
                  <div className="px-3 pb-3"><PanelFacturaElectronica ventaId={ventaId} /></div>
                )}
              </div>
            )}
          </div>
          
          {ventaEstado === 'CONFIRMADA' && tipoDocumento !== 'FE' && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800">
              <p className="font-medium mb-1">📱 WhatsApp - Enlace inteligente:</p>
              <p className="mb-1">• Se genera un PDF único al presionar el botón</p>
              <p className="mb-1">• El cliente puede descargar el documento por 30 días</p>
              <p>• Si vuelves a enviar, se reutiliza el mismo enlace (sin duplicados)</p>
            </div>
          )}
          
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {tipoDocumento === 'FE' ? 'Cerrar' : 'Cancelar'}
            </Button>
            {ventaEstado === 'CONFIRMADA' && tipoDocumento !== 'FE' && (
              <Button 
                onClick={handleSendWhatsApp}
                variant="outline"
                disabled={loading || !tipoDocumento}
                className="bg-green-50 text-green-700 hover:bg-green-100 hover:text-green-800 border-green-200"
                title="Enviar resumen por WhatsApp (solo texto)"
              >
                <Send className="mr-2 h-4 w-4" />
                WhatsApp
              </Button>
            )}
            {tipoDocumento !== 'FE' && <Button 
              onClick={handlePrint}
              disabled={loading || !tipoDocumento}
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              <Printer className="mr-2 h-4 w-4" />
              Imprimir
            </Button>}
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
