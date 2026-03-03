import React, { useState } from 'react';
import { format, parseISO, isValid } from 'date-fns';
import { es } from 'date-fns/locale';
import { CalendarIcon } from 'lucide-react';
import { Button } from './button';
import { Calendar } from './calendar';
import { Popover, PopoverContent, PopoverTrigger } from './popover';
import { cn } from '@/lib/utils';

/**
 * DatePickerInput – reemplaza los <Input type="date" /> con un calendario visual.
 *
 * Props:
 *   value      – string en formato "YYYY-MM-DD" o ""
 *   onChange   – función que recibe string "YYYY-MM-DD" o ""
 *   placeholder – texto cuando no hay fecha seleccionada
 *   className  – clases extra para el botón trigger
 *   disabled   – boolean
 */
export function DatePickerInput({
  value,
  onChange,
  placeholder = 'Seleccionar fecha',
  className,
  disabled = false,
}) {
  const [open, setOpen] = useState(false);

  const selectedDate = value ? parseISO(value) : undefined;
  const dateIsValid = selectedDate && isValid(selectedDate);

  const handleSelect = (date) => {
    if (date) {
      onChange(format(date, 'yyyy-MM-dd'));
    } else {
      onChange('');
    }
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn(
            'w-full justify-start text-left font-normal',
            !dateIsValid && 'text-muted-foreground',
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4 shrink-0" />
          {dateIsValid
            ? format(selectedDate, 'dd/MM/yyyy', { locale: es })
            : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 z-50" align="start">
        <Calendar
          mode="single"
          selected={dateIsValid ? selectedDate : undefined}
          onSelect={handleSelect}
          initialFocus
          locale={es}
        />
      </PopoverContent>
    </Popover>
  );
}
