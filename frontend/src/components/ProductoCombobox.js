import React from 'react';
import ComboboxRemoto from './ComboboxRemoto';

// Selector de producto con búsqueda en el servidor (GET /productos/buscar: nombre, código o ID).
// `value` es el producto elegido (objeto completo, con stock_total, precios, etc.) o null.
const ProductoCombobox = ({ renderDetalle, placeholder = 'Buscar producto...', ...props }) => (
  <ComboboxRemoto
    ruta="/productos/buscar"
    etiqueta={(p) => p.nombre}
    placeholder={placeholder}
    placeholderBusqueda="Buscar por nombre o código..."
    textoVacio="No se encontró el producto."
    renderItem={(p) => (
      <>
        <span className="truncate">{p.nombre}</span>
        {renderDetalle ? renderDetalle(p) : p.codigo_barra && (
          <span className="text-xs text-muted-foreground">Código: {p.codigo_barra}</span>
        )}
      </>
    )}
    {...props}
  />
);

export default ProductoCombobox;
