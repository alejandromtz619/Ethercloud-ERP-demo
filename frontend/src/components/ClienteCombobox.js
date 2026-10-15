import React from 'react';
import ComboboxRemoto from './ComboboxRemoto';

export const nombreCliente = (c) => `${c.nombre} ${c.apellido || ''}`.trim();

// Selector de cliente con búsqueda en el servidor (GET /clientes/buscar: nombre, apellido,
// RUC, cédula, teléfono o ID). `value` es el cliente elegido (objeto completo) o null.
const ClienteCombobox = ({ placeholder = 'Buscar cliente...', ...props }) => (
  <ComboboxRemoto
    ruta="/clientes/buscar"
    etiqueta={nombreCliente}
    placeholder={placeholder}
    placeholderBusqueda="Nombre, RUC o cédula..."
    textoVacio="No se encontró el cliente."
    renderItem={(c) => (
      <>
        <span className="truncate">{nombreCliente(c)}</span>
        <span className="text-xs text-muted-foreground">
          {c.ruc ? `RUC: ${c.ruc}` : c.cedula ? `CI: ${c.cedula}` : `ID: ${c.id}`}
        </span>
      </>
    )}
    {...props}
  />
);

export default ClienteCombobox;
