import React, { useState, useEffect } from 'react';
import { Clock as ClockIcon } from 'lucide-react';

const Clock = ({ className = "" }) => {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Formatear hora en formato 24h: HH:MM:SS
  const formatTime = (date) => {
    return date.toLocaleTimeString('es-PY', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'America/Asuncion' // Timezone de Paraguay
    });
  };

  // Formatear fecha: DD/MM/YYYY
  const formatDate = (date) => {
    return date.toLocaleDateString('es-PY', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: 'America/Asuncion'
    });
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <ClockIcon className="h-4 w-4 text-muted-foreground" />
      <div className="flex flex-col leading-tight">
        <span className="font-mono text-sm font-semibold text-foreground">
          {formatTime(time)}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {formatDate(time)}
        </span>
      </div>
    </div>
  );
};

export default Clock;
