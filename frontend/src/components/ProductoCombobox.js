import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from './ui/button';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from './ui/command';
import { cn } from '../lib/utils';

const POR_PAGINA = 20;

// Selector de producto con búsqueda en el servidor (GET /productos/buscar).
// Reemplaza cargar el catálogo completo en cada pantalla, que con miles de productos
// descargaba decenas de MB y dibujaba miles de opciones.
// `value` es el producto elegido (objeto completo, con stock_total, precios, etc.) o null.
const ProductoCombobox = ({
  value,
  onChange,
  placeholder = 'Buscar producto...',
  disabled = false,
  className,
  contentClassName = 'w-[400px]',
  renderDetalle,
}) => {
  const { api, empresa } = useApp();
  const [open, setOpen] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [resultado, setResultado] = useState({ items: [], total: 0 });
  const [cargando, setCargando] = useState(false);
  const ultimoPedido = useRef(0);

  useEffect(() => {
    if (!open || !empresa?.id) return undefined;
    const pedido = ++ultimoPedido.current;
    const texto = busqueda.trim();
    const timer = setTimeout(async () => {
      setCargando(true);
      try {
        const params = new URLSearchParams({ empresa_id: empresa.id, limit: POR_PAGINA });
        if (texto) params.set('q', texto);
        const data = await api(`/productos/buscar?${params}`);
        if (pedido === ultimoPedido.current) setResultado(data);
      } catch (e) {
        if (pedido === ultimoPedido.current) setResultado({ items: [], total: 0 });
      } finally {
        if (pedido === ultimoPedido.current) setCargando(false);
      }
    }, texto ? 250 : 0);
    return () => clearTimeout(timer);
  }, [open, busqueda, empresa?.id, api]);

  const cambiarApertura = (abierto) => {
    setOpen(abierto);
    if (!abierto) setBusqueda('');
  };

  return (
    <Popover open={open} onOpenChange={cambiarApertura}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className={cn('w-full justify-between font-normal', className)}
        >
          <span className="truncate">{value ? value.nombre : placeholder}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className={cn('p-0', contentClassName)}>
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Buscar por nombre o código..."
            value={busqueda}
            onValueChange={setBusqueda}
          />
          {cargando && resultado.items.length === 0 ? (
            <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Buscando...
            </div>
          ) : (
            <CommandEmpty>No se encontró el producto.</CommandEmpty>
          )}
          <CommandGroup className="max-h-64 overflow-auto">
            {resultado.items.map((p) => (
              <CommandItem
                key={p.id}
                value={String(p.id)}
                onSelect={() => {
                  onChange(p);
                  cambiarApertura(false);
                }}
              >
                <Check className={cn('mr-2 h-4 w-4', value?.id === p.id ? 'opacity-100' : 'opacity-0')} />
                <div className="flex flex-col min-w-0">
                  <span className="truncate">{p.nombre}</span>
                  {renderDetalle ? renderDetalle(p) : p.codigo_barra && (
                    <span className="text-xs text-muted-foreground">Código: {p.codigo_barra}</span>
                  )}
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
          {resultado.total > resultado.items.length && (
            <div className="border-t px-3 py-2 text-xs text-muted-foreground">
              Mostrando {resultado.items.length} de {resultado.total.toLocaleString('es-PY')} — escriba para afinar la búsqueda
            </div>
          )}
        </Command>
      </PopoverContent>
    </Popover>
  );
};

export default ProductoCombobox;
