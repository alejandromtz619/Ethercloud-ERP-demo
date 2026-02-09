# Ajustes de Impresión - Luz Brill ERP (Epson LX-350)

## 📋 Resumen de Cambios

Se han ajustado los formatos de **boleta** y **factura** para que funcionen correctamente con la impresora **Epson LX-350** (matriz de puntos / dot matrix) usando papel continuo de **240mm de ancho**.

## 🖨️ Especificaciones de la Impresora

**Modelo**: Epson LX-350  
**Tipo**: Matriz de puntos (Dot Matrix)  
**Papel**: Papel continuo con perforaciones laterales  
**Ancho**: 240mm (24cm)  
**Boleta**: 240mm x 140mm  
**Factura**: 240mm x altura variable (papel pre-impreso)

## 🔧 Cambios Realizados

### Boleta (Papel Continuo 240mm x 140mm)

#### Dimensiones Ajustadas:
- **Ancho**: 240mm (papel continuo standard)
- **Alto**: 140mm (formato boleta)
- **Márgenes**: 8mm arriba/abajo, 10mm izq/der
- **Fuente base**: Courier New (monoespaciada, ideal para matriz de puntos)

#### Tamaños de Fuente Optimizados:
- **Título "LuzBrill"**: 22px bold + subrayado + letter-spacing 2px
- **Teléfonos/info**: 11px bold
- **Número de nota**: 13px bold
- **Datos del cliente**: 11px con negrita en etiquetas
- **Tabla de productos**:
  - Headers: 10px bold con borde superior/inferior de 2px
  - Contenido: 10px, precios en bold
  - Padding: 3-4px para legibilidad
- **Totales**: 11px para líneas normales, 14px bold para total final
- **Pie de firma**: 11-12px bold
- **Advertencia final**: 9px bold italic

#### Mejoras para Matriz de Puntos:
- Fuente **Courier New** monoespaciada (mejor legibilidad en matriz de puntos)
- Bordes más gruesos: **2px solid** en lugar de 1px
- **Border doble (3px double)** antes del total final
- **font-weight: bold** en todos los textos importantes
- **letter-spacing** aumentado en títulos
- **textDecoration: underline** en título principal
- Espaciado generoso para compensar menor resolución

### Factura (Papel Continuo Pre-impreso 240mm)

#### Dimensiones y Márgenes:
- **Ancho**: 240mm (igual que boleta)
- **Alto**: Variable según contenido (mínimo 200mm)
- **Papel**: Pre-impreso con membrete de la empresa
- **Márgenes**:
  - Superior/Inferior: 10mm
  - Izquierda/Derecha: 12mm
- **Fuente**: Courier New (monoespaciada)

#### Tamaños de Fuente:
- **Base**: 12px
- **Título empresa**: 22px bold subrayado + letter-spacing 2px
- **Subtítulos**: 12px bold
- **"FACTURA"**: 18px bold + letter-spacing
- **Número de factura**: 16px bold
- **Headers de tabla**: 11px bold
- **Contenido de tabla**: 11px, precios en bold
- **Totales**: 12px bold, total final 14px bold
- **Firmas**: 11-12px bold

#### Mejoras Visuales:
- Cuadro de factura con `border: 3px double black`
- Fuente monoespaciada **Courier New** para mejor legibilidad
- **Negrita intensiva** en todos los campos importantes
- Bordes más gruesos (2px) para mejor visibilidad
- Sin backgrounds de color (matriz de puntos no imprime grises bien)
- Líneas de firma con texto subrayado
- `marginTop: '20mm'` antes de firmas

## ⚙️ Configuración de Impresora Epson LX-350

### Configuración Recomendada para Papel Continuo 240mm:

1. **En Windows (Panel de Control → Dispositivos e Impresoras)**:
   - Clic derecho en "Epson LX-350" → Propiedades → Preferencias de impresión
   - Configurar:
     - **Tamaño de papel**: Personalizado o Continuo
     - **Ancho**: 9.45" (240mm) o "Wide continuous"
     - **Alto boleta**: 5.51" (140mm)
     - **Alto factura**: Variable/Continuo
     - **Márgenes**: Mínimo posible
     - **Orientación**: Vertical (Portrait)
     - **Calidad**: Borrador o Normal (Normal para mejor legibilidad)
     - **Fuente interna**: Desactivar (usar fuente del documento)

2. **En navegador (al imprimir)**:
   - Abrir diálogo de impresión (Ctrl+P)
   - Seleccionar "Epson LX-350"
   - **Configuración importante**:
     - ✅ Tamaño: Personalizado 240mm ancho
     - ✅ Márgenes: Ninguno o Mínimo
     - ✅ Escala: 100% (NUNCA ajustar)
     - ❌ NO marcar "Ajustar a página"
     - ❌ NO marcar "Encabezados y pies de página"
     - ✅ Imprimir fondos: NO (matriz de puntos no imprime bien grises)

3. **Configuración de Driver Epson**:
   - En propiedades avanzadas:
     - Velocidad: Normal (evitar modo rápido que reduce calidad)
     - Resolución: 360 dpi (máxima calidad)
     - Alimentación: Papel continuo con tractor
     - Formato: Personalizado 240mm

## 🎯 Características del Formato Actual

| Elemento | Configuración |
|----------|---------------|
| **Impresora** | Epson LX-350 (Matriz de Puntos) |
| **Ancho papel** | 240mm (continuo) |
| **Alto boleta** | 140mm |
| **Alto factura** | Variable (papel pre-impreso) |
| **Fuente principal** | Courier New (monoespaciada) |
| **Font base boleta** | 12px |
| **Font base factura** | 12px |
| **Font título** | 22px bold subrayado |
| **Font tabla** | 10-11px bold en precios |
| **Márgenes boleta** | 8mm/10mm |
| **Márgenes factura** | 10mm/12mm |
| **Bordes** | 2-3px para visibilidad |
| **Negrita** | Extensiva en todos los campos importantes |
| **Espaciado** | Generoso para legibilidad en matriz de puntos |

## 🚀 Cómo Usar

### Para Imprimir Boleta:
1. Crear una venta en el módulo de Ventas
2. Hacer clic en "Imprimir"
3. Seleccionar "Boleta"
4. Verificar en vista previa que el ancho sea correcto
5. Imprimir en impresora térmica

### Para Imprimir Factura:
1. Crear una venta con cliente que tiene RUC
2. Hacer clic en "Imprimir"
3. Seleccionar "Factura"
4. Verificar en vista previa (debería verse en formato A4)
5. Imprimir en impresora A4 normal

## 🔍 Solución de Problemas

### Problema: El texto se corta en los bordes
**Solución**: 
- Verificar que el ancho de papel esté configurado en 240mm (9.45")
- Asegurar que la alimentación sea por tractor (papel continuo)
- En navegador, márgenes en "Ninguno"
- Verificar que la escala esté en 100%

### Problema: Las letras se ven muy tenues o poco legibles
**Solución**:
- Cambiar cinta de impresora (las cintas gastadas producen texto tenue)
- En configuración de impresora, usar modo "Normal" en lugar de "Borrador"
- Aumentar la densidad de impresión desde el panel de control de la impresora
- Verificar que el ajuste de grosor esté en posición correcta (palanca en la impresora)

### Problema: El formato no coincide con el papel pre-impreso (facturas)
**Solución**:
- Medir físicamente los márgenes del papel pre-impreso
- Ajustar los valores `padding` en `FacturaPrint` component
- Usar regla para medir la posición exacta donde debe empezar el texto
- Ajustar `marginTop` y `marginBottom` específicos

### Problema: La impresora no alimenta el papel correctamente
**Solución**:
- Verificar que las perforaciones laterales estén bien enganchadas en los tractores
- Ajustar la tensión del papel (ni muy flojo ni muy tenso)
- En propiedades de impresora, seleccionar "Papel continuo con tractor"
- Limpiar los rodillos de alimentación

### Problema: Caracteres extraños o símbolos en lugar de texto
**Solución**:
- Verificar que el driver Epson LX-350 esté correctamente instalado
- Actualizar driver desde sitio oficial de Epson
- En configurar impresora → Set de caracteres → Seleccionar "PC-850 Multilingual"
- Reiniciar el spooler de impresión: `net stop spooler && net start spooler`

### Problema: Se desperdicia mucho papel entre documentos
**Solución**:
- Activar "Salto de página automático" en las propiedades del driver
- Configurar corte automático después de imprimir
- Usar el botón "Form Feed" de la impresora para expulsar la hoja después de imprimir

## 📝 Archivos Modificados

- `frontend/src/components/PrintModal.js`: Componente principal con ajustes de formato

### Secciones Modificadas:
1. **BoletaPrint component** (líneas ~16-130):
   - Ancho reducido a 72mm
   - Fuentes reducidas (8-18px)
   - Márgenes en milímetros
   - Padding eliminado del contenedor principal
   - Tabla optimizada con menos padding

2. **FacturaPrint component** (líneas ~133-250):
   - Dimensiones A4 explícitas (210mm x 297mm)
   - Márgenes 15mm/12mm
   - Fuentes reducidas (9-20px)
   - Espaciado en milímetros

3. **Estilos de impresión** (líneas ~305-345):
   - Página con `margin: 0`
   - Estilos específicos para `.boleta-print` y `.factura-print`
   - Reglas `@page` y `@media print`
   - Prevención de cortes de página en tablas

## 🎨 Referencia Visual

```
┌──────────────────────────────────────────────┐
│             240mm de ancho                   │
├──────────────────────────────────────────────┤
│ 10mm |                                | 10mm │ ← Márgenes laterales
│      |         LuzBrill                |     │
│      |       (22px bold)               |     │
│      |     Tel: 061 572516...          |     │
│      |─────────────────────────────────|     │
│      |     NOTA NRO: 001-001-0000001   |     │ 140mm
│      |═════════════════════════════════|     │ alto
│      | Razon Social: Juan Perez        |     │
│      | Dirección: Av. San Blas 123     |     │
│      | [más datos del cliente...]      |     │
│      |═════════════════════════════════|     │
│      | Cod | Cant | Desc | IVA | Prec  |     │
│      |═════════════════════════════════|     │
│      | 001 | 2.00 | Prod |  10 | 15000 |     │
│      | ... | .... | .... | ... | ..... |     │
│      |─────────────────────────────────|     │
│      | Subtotal:            150.000 Gs |     │
│      | En Letras: CIENTO CIN...        |     │
│      |═════════════════════════════════|     │
│      | TOTAL A PAGAR:       150.000 Gs |     │
│      |                                 |     │
│      | ___________________________     |     │
│      |       Firma Cliente             |     │
│      | Favor Conferir Su Mercaderia... |     │
└──────────────────────────────────────────────┘

Papel continuo con perforaciones laterales
═══ = Borde doble (3px)
─── = Borde simple (2px)
```

## ✅ Testing

Probar con:
1. ✅ Venta simple (1-3 productos)
2. ✅ Venta grande (10+ productos)
3. ✅ Cliente con nombre largo
4. ✅ Productos con descripción larga
5. ✅ Venta con descuento
6. ✅ Factura con todos los campos llenos

## 📌 Notas Adicionales

- **Epson LX-350**: Impresora de matriz de puntos (9 pines, 80 columnas, 360 dpi)
- **Papel continuo**: 240mm ancho con perforaciones laterales para tractor
- **Boleta**: 140mm de alto, papel blanco estándar
- **Factura**: Papel pre-impreso con membrete, altura variable
- Los formatos están optimizados con:
  - Fuente **Courier New** monoespaciada (mejor para matriz de puntos)
  - **Negrita intensiva** para mejor visibilidad
  - **Bordes más gruesos** (2-3px) para compensar menor resolución
  - **Espaciado generoso** para legibilidad
- **Importante**: La matriz de puntos NO imprime bien backgrounds grises (se ven rayados), por eso se eliminaron
- El formato actual es compatible con Paraguay: moneda PYG, IVA 10%
- Los PDFs de muestra pueden verse en `dump_old/muestra boleta.pdf` y `dump_old/muestra factura.pdf`

### Mantenimiento de la Impresora:
1. **Cambiar cinta**: Cada 3-6 meses o cuando se vea tenue
2. **Limpiar cabezal**: Mensualmente con alcohol isopropílico y bastoncillo
3. **Lubricar tractores**: Cada 6 meses con aceite para máquinas de oficina
4. **Ajustar alineación**: Si el texto sale torcido, ajustar guías laterales

## 🔄 Próximos Pasos (Opcionales)

Si los ajustes actuales no coinciden exactamente con el papel pre-impreso de facturas:

1. **Imprimir una prueba de cada documento**
2. **Comparar con documentos del sistema anterior**
3. **Medir físicamente con regla**:
   - Margen superior (donde empieza el membrete)
   - Margen izquierdo
   - Posición de cada campo si es papel pre-impreso
4. **Ajustar valores en** [PrintModal.js](frontend/src/components/PrintModal.js):
   - `padding: '10mm 12mm'` → Cambiar a medidas exactas
   - `fontSize` → Aumentar/reducir si no coincide
   - `marginTop/marginBottom` → Ajustar espacios entre secciones
   - `lineHeight` → Modificar si las líneas están muy juntas/separadas

5. **Para papel pre-impreso de facturas**:
   - Si el membrete ya está impreso, reducir/eliminar el header
   - Ajustar posición de inicio del contenido con `marginTop`
   - Alinear cada campo con las zonas del formulario pre-impreso

---

**Fecha de creación**: 9 de febrero de 2026  
**Versión**: 2.0 (Actualizado para Epson LX-350)  
**Impresora**: Epson LX-350 (Matriz de Puntos)  
**Papel**: Continuo 240mm x 140mm (boleta), 240mm x variable (factura pre-impresa)
