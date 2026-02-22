import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Separator } from '../components/ui/separator';
import { Badge } from '../components/ui/badge';
import { Settings, Sun, Moon, Palette, Phone, User, DollarSign, RefreshCw, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const colorOptions = [
  { id: 'blue', name: 'Azul', hex: '#0044CC' },
  { id: 'green', name: 'Verde', hex: '#10B981' },
  { id: 'purple', name: 'Púrpura', hex: '#8B5CF6' },
  { id: 'red', name: 'Rojo', hex: '#EF4444' },
  { id: 'orange', name: 'Naranja', hex: '#F97316' },
  { id: 'teal', name: 'Turquesa', hex: '#14B8A6' },
  { id: 'ether', name: 'Ether Dark', hex: '#000000', dark: true },
];

const Sistema = () => {
  const { user, theme, setTheme, primaryColor, setPrimaryColor, api } = useApp();
  const [saving, setSaving] = useState(false);
  
  // Currency exchange state
  const [cotizacion, setCotizacion] = useState(null);
  const [loadingCotizacion, setLoadingCotizacion] = useState(true);
  const [manualMode, setManualMode] = useState(false);
  const [manualUsd, setManualUsd] = useState('');
  const [manualBrl, setManualBrl] = useState('');
  const [savingCotizacion, setSavingCotizacion] = useState(false);

  useEffect(() => {
    fetchCotizacion();
  }, []);

  const fetchCotizacion = async () => {
    setLoadingCotizacion(true);
    try {
      const data = await api('/cotizacion');
      setCotizacion(data);
      setManualMode(data.manual);
      if (data.manual) {
        setManualUsd(data.usd_pyg?.toString() || '');
        setManualBrl(data.brl_pyg?.toString() || '');
      }
    } catch (e) {
      toast.error('Error al cargar cotización');
    } finally {
      setLoadingCotizacion(false);
    }
  };

  const handleSaveManualCotizacion = async () => {
    if (!manualUsd || !manualBrl) {
      toast.error('Ingrese ambas cotizaciones');
      return;
    }
    
    setSavingCotizacion(true);
    try {
      await api('/cotizacion/manual', {
        method: 'POST',
        body: JSON.stringify({
          usd_pyg: parseFloat(manualUsd),
          brl_pyg: parseFloat(manualBrl),
          manual: true
        })
      });
      toast.success('Cotización manual guardada');
      fetchCotizacion();
    } catch (e) {
      toast.error('Error al guardar cotización');
    } finally {
      setSavingCotizacion(false);
    }
  };

  const handleActivateAutoCotizacion = async () => {
    setSavingCotizacion(true);
    try {
      await api('/cotizacion/auto', { method: 'POST' });
      toast.success('Cotización automática activada');
      setManualMode(false);
      fetchCotizacion();
    } catch (e) {
      toast.error('Error al activar cotización automática');
    } finally {
      setSavingCotizacion(false);
    }
  };

  const handleSavePreferences = async () => {
    if (!user?.id) return;
    
    setSaving(true);
    try {
      await api('/preferencias', {
        method: 'POST',
        body: JSON.stringify({
          usuario_id: user.id,
          tema: theme,
          color_primario: colorOptions.find(c => c.id === primaryColor)?.hex || '#0044CC'
        })
      });
      toast.success('Preferencias guardadas');
    } catch (e) {
      toast.error('Error al guardar preferencias');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl" data-testid="sistema-page">
      <div>
        <h1 className="text-2xl font-bold">Configuración del Sistema</h1>
        <p className="text-muted-foreground">Personaliza tu experiencia en Luz Brill ERP</p>
      </div>

      {/* Theme Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Apariencia
          </CardTitle>
          <CardDescription>
            Estas preferencias son solo para tu usuario y no afectan a otros
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Dark Mode Toggle */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {theme === 'dark' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
              <div>
                <Label>Modo Oscuro</Label>
                <p className="text-sm text-muted-foreground">
                  Cambia entre tema claro y oscuro
                </p>
              </div>
            </div>
            <Switch
              checked={theme === 'dark'}
              onCheckedChange={(checked) => setTheme(checked ? 'dark' : 'light')}
              data-testid="theme-switch"
            />
          </div>

          <Separator />

          {/* Color Selection */}
          <div>
            <Label className="mb-3 block">Color Principal</Label>
            <div className="grid grid-cols-7 gap-3">
              {colorOptions.map((color) => (
                <button
                  key={color.id}
                  onClick={() => {
                    setPrimaryColor(color.id);
                    if (color.dark) {
                      setTheme('dark');
                      document.documentElement.setAttribute('data-theme', 'ether');
                    } else {
                      document.documentElement.removeAttribute('data-theme');
                    }
                  }}
                  className={cn(
                    "w-full aspect-square rounded-lg transition-all relative",
                    "hover:scale-105 hover:shadow-lg",
                    primaryColor === color.id && "ring-2 ring-offset-2 ring-foreground",
                    color.dark && "border-2 border-white"
                  )}
                  style={{ backgroundColor: color.hex }}
                  title={color.name}
                  data-testid={`color-${color.id}`}
                >
                  {color.dark && (
                    <span className="absolute inset-0 flex items-center justify-center text-white text-xs font-bold">
                      &lt;
                    </span>
                  )}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Color actual: {colorOptions.find(c => c.id === primaryColor)?.name || 'Azul'}
            </p>
          </div>

          <Button onClick={handleSavePreferences} disabled={saving} className="w-full">
            {saving ? 'Guardando...' : 'Guardar Preferencias'}
          </Button>
        </CardContent>
      </Card>

      {/* Currency Exchange Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Cotización de Divisas
          </CardTitle>
          <CardDescription>
            Configure la cotización USD/PYG y BRL/PYG
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingCotizacion ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <>
              {/* Current Values */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-secondary rounded-lg">
                <div>
                  <p className="text-xs text-muted-foreground">USD → PYG</p>
                  <p className="font-mono-data text-lg font-semibold">
                    {cotizacion?.usd_pyg ? Number(cotizacion.usd_pyg).toLocaleString('es-PY') : '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">BRL → PYG</p>
                  <p className="font-mono-data text-lg font-semibold">
                    {cotizacion?.brl_pyg ? Number(cotizacion.brl_pyg).toLocaleString('es-PY') : '-'}
                  </p>
                </div>
              </div>

              {/* Mode Indicator */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant={cotizacion?.manual ? "secondary" : "default"}>
                    {cotizacion?.manual ? 'Manual' : 'Automático'}
                  </Badge>
                  {cotizacion?.fecha_actualizacion && (
                    <span className="text-xs text-muted-foreground">
                      Actualizado: {new Date(cotizacion.fecha_actualizacion).toLocaleString('es-PY')}
                    </span>
                  )}
                </div>
                {!cotizacion?.manual && (
                  <Button variant="outline" size="sm" onClick={fetchCotizacion}>
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Actualizar
                  </Button>
                )}
              </div>

              <Separator />

              {/* Manual Mode Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <Label>Modo Manual</Label>
                  <p className="text-sm text-muted-foreground">
                    Ingresar cotización manualmente
                  </p>
                </div>
                <Switch
                  checked={manualMode}
                  onCheckedChange={(checked) => {
                    setManualMode(checked);
                    if (!checked) handleActivateAutoCotizacion();
                  }}
                  data-testid="manual-cotizacion-switch"
                />
              </div>

              {/* Manual Input Fields */}
              {manualMode && (
                <div className="space-y-4 p-4 border rounded-lg">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>USD → PYG</Label>
                      <Input
                        type="number"
                        placeholder="Ej: 7500"
                        value={manualUsd}
                        onChange={(e) => setManualUsd(e.target.value)}
                        data-testid="manual-usd-input"
                      />
                    </div>
                    <div>
                      <Label>BRL → PYG</Label>
                      <Input
                        type="number"
                        placeholder="Ej: 1500"
                        value={manualBrl}
                        onChange={(e) => setManualBrl(e.target.value)}
                        data-testid="manual-brl-input"
                      />
                    </div>
                  </div>
                  <Button 
                    onClick={handleSaveManualCotizacion} 
                    disabled={savingCotizacion}
                    className="w-full"
                  >
                    {savingCotizacion && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                    Guardar Cotización Manual
                  </Button>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Support Contact */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Soporte Técnico
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-secondary p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-6 w-6 text-primary" />
              </div>
              <div>
                <p className="font-medium">Alejandro Martinez</p>
                <p className="text-sm text-muted-foreground">Ether - Soporte Técnico</p>
                <p className="text-primary font-mono mt-1">0976 574 271</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* System Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Información del Sistema
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Versión</span>
              <span className="font-mono">1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Usuario</span>
              <span>{user?.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">IVA Paraguay</span>
              <span className="font-mono">10%</span>
            </div>
            <Separator className="my-2" />
            <p className="text-xs text-muted-foreground text-center">
              Luz Brill ERP © 2024 - Sistema de Gestión Empresarial
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Sistema;
