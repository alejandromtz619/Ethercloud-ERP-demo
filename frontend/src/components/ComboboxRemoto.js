import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Button } from './ui/button';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from './ui/command';
import { cn } from '../lib/utils';

// Selector con búsqueda en el servidor. `ruta` es una búsqueda paginada que acepta
// empresa_id, q y limit y devuelve { items, total } (p. ej. /productos/buscar).
// Reemplaza descargar listas completas, que con miles de registros trababan la pantalla.
// `value` es el elemento elegido (objeto completo) o null.
const ComboboxRemoto = ({
  ruta,
  value,
  onChange,
  etiqueta,
  renderItem,
  excluir,
  placeholder = 'Buscar...',
  placeholderBusqueda = 'Buscar...',
  textoVacio = 'Sin resultados.',
  porPagina = 20,
  disabled = false,
  className,
  contentClassName = 'w-[400px]',
  align,
  dataTestId,
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
        const params = new URLSearchParams({ empresa_id: empresa.id, limit: porPagina });
        if (texto) params.set('q', texto);
        const data = await api(`${ruta}?${params}`);
        if (pedido === ultimoPedido.current) setResultado(data);
      } catch (e) {
        if (pedido === ultimoPedido.current) setResultado({ items: [], total: 0 });
      } finally {
        if (pedido === ultimoPedido.current) setCargando(false);
      }
    }, texto ? 250 : 0);
    return () => clearTimeout(timer);
  }, [open, busqueda, empresa?.id, api, ruta, porPagina]);

  const cambiarApertura = (abierto) => {
    setOpen(abierto);
    if (!abierto) setBusqueda('');
  };

  const items = excluir ? resultado.items.filter((x) => !excluir(x)) : resultado.items;

  return (
    <Popover open={open} onOpenChange={cambiarApertura}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          // Un combobox no toma su nombre del texto interno: sin esto los lectores de pantalla no lo anuncian
          aria-label={value ? etiqueta(value) : placeholder}
          disabled={disabled}
          className={cn('w-full justify-between font-normal', className)}
          data-testid={dataTestId}
        >
          <span className="truncate">{value ? etiqueta(value) : placeholder}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className={cn('p-0', contentClassName)} align={align}>
        <Command shouldFilter={false}>
          <CommandInput placeholder={placeholderBusqueda} value={busqueda} onValueChange={setBusqueda} />
          {cargando && items.length === 0 ? (
            <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Buscando...
            </div>
          ) : (
            <CommandEmpty>{textoVacio}</CommandEmpty>
          )}
          <CommandGroup className="max-h-64 overflow-auto">
            {items.map((item) => (
              <CommandItem
                key={item.id}
                value={String(item.id)}
                onSelect={() => {
                  onChange(item);
                  cambiarApertura(false);
                }}
              >
                <Check className={cn('mr-2 h-4 w-4 shrink-0', value?.id === item.id ? 'opacity-100' : 'opacity-0')} />
                <div className="flex flex-col min-w-0">{renderItem(item)}</div>
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

export default ComboboxRemoto;
