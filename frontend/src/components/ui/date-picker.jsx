import * as React from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Calendar as CalendarIcon } from "lucide-react";

import { cn } from "../../lib/utils";
import { Button } from "./button";
import { Calendar } from "./calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./popover";

export function DatePicker({ date, onDateChange, placeholder = "Seleccionar fecha", className }) {
  const [open, setOpen] = React.useState(false);

  const handleSelect = (selectedDate) => {
    if (selectedDate) {
      // Convert Date object to YYYY-MM-DD string
      const dateString = format(selectedDate, "yyyy-MM-dd");
      onDateChange(dateString);
      setOpen(false);
    }
  };

  // Convert string date to Date object for calendar
  const dateValue = date ? new Date(date + 'T00:00:00') : undefined;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          className={cn(
            "justify-start text-left font-normal",
            !date && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {date ? format(dateValue, "dd/MM/yyyy", { locale: es }) : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={dateValue}
          onSelect={handleSelect}
          initialFocus
          locale={es}
        />
      </PopoverContent>
    </Popover>
  );
}
