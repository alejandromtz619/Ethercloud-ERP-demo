import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

// Primer uso de una instancia nueva: datos de la empresa y primer administrador, con la contraseña que
// elija. Pide el código de alta que da Ether (CODIGO_ALTA del servidor). Funciona una sola vez.

const VACIO = {
  codigo: '',
  empresa: { nombre: '', ruc: '', direccion: '', telefono: '', email: '' },
  administrador: { nombre: '', apellido: '', email: '', password: '', repetir: '' },
};

const Alta = () => {
  const { login, API_URL } = useApp();
  const [estado, setEstado] = useState(null); // { pendiente, codigo_configurado }
  const [datos, setDatos] = useState(VACIO);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    fetch(`${API_URL}/alta`).then((r) => r.json()).then(setEstado).catch(() => setEstado({ pendiente: false }));
  }, [API_URL]);

  if (estado && !estado.pendiente) return <Navigate to="/login" replace />;

  const campo = (seccion, clave, etiqueta, extra = {}) => (
    <div className="space-y-1.5">
      <Label htmlFor={`${seccion}-${clave}`}>{etiqueta}</Label>
      <Input id={`${seccion}-${clave}`} data-testid={`alta-${seccion}-${clave}`} value={datos[seccion][clave]}
             onChange={(e) => setDatos({ ...datos, [seccion]: { ...datos[seccion], [clave]: e.target.value } })} {...extra} />
    </div>
  );

  const enviar = async (e) => {
    e.preventDefault();
    if (datos.administrador.password !== datos.administrador.repetir) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    setEnviando(true);
    try {
      const { repetir, ...administrador } = datos.administrador;
      const res = await fetch(`${API_URL}/alta`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codigo: datos.codigo, empresa: datos.empresa, administrador }),
      });
      const cuerpo = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detalle = Array.isArray(cuerpo.detail) ? 'Revisá los datos obligatorios' : cuerpo.detail;
        throw new Error(detalle || `Error ${res.status}`);
      }
      // Con la sesión iniciada, la ruta /alta lleva a Configuración (App.js)
      await login(administrador.email, administrador.password);
      toast.success('¡Listo! El sistema quedó configurado');
    } catch (err) {
      toast.error(err.message);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-cover bg-center"
         style={{ backgroundImage: "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.7)), url('/lago-republica.jpg')" }}>
      <Card className="w-full max-w-2xl shadow-2xl" style={{ backgroundColor: 'white' }} data-testid="alta-card">
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-gray-900">Configuración inicial</CardTitle>
          <CardDescription>
            Es el primer uso de este sistema. Cargá los datos de la empresa y del primer administrador; después vas a
            poder sumar usuarios, roles y el resto de la configuración.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {estado === null ? (
            <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : !estado.codigo_configurado ? (
            <p className="text-sm text-destructive">Falta el código de alta en el servidor. Pedíselo a soporte de Ether.</p>
          ) : (
            <form onSubmit={enviar} className="space-y-6 text-gray-900">
              <div className="space-y-1.5">
                <Label htmlFor="alta-codigo">Código de alta</Label>
                <Input id="alta-codigo" data-testid="alta-codigo" required autoComplete="off" value={datos.codigo}
                       onChange={(e) => setDatos({ ...datos, codigo: e.target.value })} />
                <p className="text-xs text-muted-foreground">Te lo da Ether junto con el acceso al sistema.</p>
              </div>
              <fieldset className="space-y-3">
                <legend className="font-semibold">Empresa</legend>
                <div className="grid gap-3 sm:grid-cols-2">
                  {campo('empresa', 'nombre', 'Razón social', { required: true })}
                  {campo('empresa', 'ruc', 'RUC', { required: true, placeholder: '80012345-6' })}
                  {campo('empresa', 'direccion', 'Dirección')}
                  {campo('empresa', 'telefono', 'Teléfono')}
                  {campo('empresa', 'email', 'E-mail', { type: 'email' })}
                </div>
              </fieldset>
              <fieldset className="space-y-3">
                <legend className="font-semibold">Administrador</legend>
                <div className="grid gap-3 sm:grid-cols-2">
                  {campo('administrador', 'nombre', 'Nombre', { required: true })}
                  {campo('administrador', 'apellido', 'Apellido')}
                  {campo('administrador', 'email', 'E-mail (para iniciar sesión)', { required: true, type: 'email', autoComplete: 'username' })}
                  <div />
                  {campo('administrador', 'password', 'Contraseña', { required: true, type: 'password', minLength: 8, autoComplete: 'new-password' })}
                  {campo('administrador', 'repetir', 'Repetir contraseña', { required: true, type: 'password', minLength: 8, autoComplete: 'new-password' })}
                </div>
                <p className="text-xs text-muted-foreground">Al menos 8 caracteres. Nadie más la conoce: guardala bien.</p>
              </fieldset>
              <Button type="submit" className="w-full" disabled={enviando} data-testid="alta-enviar">
                {enviando && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Crear y entrar
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Alta;
