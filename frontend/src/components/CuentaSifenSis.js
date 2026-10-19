import React, { useCallback, useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { AlertTriangle, BadgeCheck, Eye, Loader2, Mail, Save, ShieldCheck, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';

// Cuenta de la empresa en SIFEN SIS (backend/fiscal/rutas.py, /api/fiscal/cuenta): estado, certificado,
// diseño y logo del KuDE, envío por correo y timbrado, sin entrar al portal del proveedor. Lo que modifica
// necesita una API key con permiso de configuración; con una de sólo emisión se ve el estado.

const fecha = (iso) => (iso ? new Date(iso).toLocaleDateString('es-PY', { timeZone: 'America/Asuncion' }) : '—');
const DATOS_EJEMPLO = { contribuyente: 'datos del contribuyente', timbrado: 'timbrado', establecimiento: 'establecimiento',
                        actividadEconomica: 'actividad económica' };

function useConToken() {
  const { token, API_URL } = useApp();
  // Pedidos que no son JSON (archivos, PDF): fetch directo con la sesión
  return useCallback(async (ruta, opciones = {}) => {
    const res = await fetch(`${API_URL}${ruta}`, { ...opciones, headers: { ...(opciones.headers || {}), Authorization: `Bearer ${token}` } });
    if (!res.ok) {
      const cuerpo = await res.json().catch(() => ({}));
      const detalle = cuerpo.detail;
      throw new Error(Array.isArray(detalle?.errores) ? detalle.errores.join(' · ') : (typeof detalle === 'string' ? detalle : `Error ${res.status}`));
    }
    return res;
  }, [token, API_URL]);
}

function Estado({ cuenta }) {
  const cert = cuenta.certificado || {};
  const pocoTiempo = cert.diasParaVencer !== undefined && cert.diasParaVencer < 30;
  const cuota = cuenta.cuota || {};
  return (
    <div className="space-y-3 text-sm" data-testid="estado-cuenta">
      <div className="flex flex-wrap gap-2">
        <Badge className={cuenta.listoParaEmitir ? 'bg-green-100 text-green-900 border-0' : 'bg-red-100 text-red-900 border-0'}>
          {cuenta.listoParaEmitir ? 'Lista para emitir' : 'Falta configurar'}
        </Badge>
        <Badge variant="secondary">{cuenta.ambiente}</Badge>
        {cuenta.timbrado && <Badge variant="outline">Timbrado {cuenta.timbrado}</Badge>}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <p className={pocoTiempo ? 'text-destructive font-medium' : ''}>
          <ShieldCheck className="inline h-4 w-4 mr-1" />
          Certificado: {cert.vigente ? `vigente hasta ${fecha(cert.validoHasta)} (${cert.diasParaVencer} días)` : 'no vigente o sin cargar'}
        </p>
        <p>Documentos este período: {cuota.usados ?? 0}{cuota.limite ? ` de ${cuota.limite}` : ' (sin tope)'}</p>
      </div>
      {(cuenta.avisos || []).length > 0 && (
        <ul className="space-y-1 rounded-md bg-amber-50 p-2 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          {cuenta.avisos.map((a, i) => <li key={i}>• {typeof a === 'string' ? a : a.mensaje || JSON.stringify(a)}</li>)}
        </ul>
      )}
    </div>
  );
}

function Kude({ configuracion }) {
  const { api } = useApp();
  const conToken = useConToken();
  const [diseno, setDiseno] = useState(() => {
    const k = configuracion.kude || {};
    return { colorPrimario: k.colorPrimario || '#114E4C', colorSecundario: k.colorSecundario || '#E5F0EF',
             colorAcento: k.colorAcento || '#0044CC', colorTexto: k.colorTexto || '#111111', textoPie: k.textoPie || '',
             tamanoLogo: k.tamanoLogo || 'm', mostrarQr: k.mostrarQr ?? true, mostrarTimbrado: k.mostrarTimbrado ?? true,
             mostrarLiquidacion: k.mostrarLiquidacion ?? true, esquinasRedondeadas: k.esquinasRedondeadas ?? false };
  });
  const [vista, setVista] = useState(null); // { url, ejemplo }
  const [logo, setLogo] = useState(null);
  const [trabajando, setTrabajando] = useState('');

  const cargarLogo = useCallback(async () => {
    try {
      const res = await conToken('/fiscal/cuenta/kude/logo');
      setLogo(URL.createObjectURL(await res.blob()));
    } catch { setLogo(null); }
  }, [conToken]);
  useEffect(() => { cargarLogo(); }, [cargarLogo]);

  const verVista = async (formato) => {
    setTrabajando(`vista-${formato}`);
    try {
      const res = await conToken('/fiscal/cuenta/kude/vista-previa', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ formato, diseno }),
      });
      const ejemplo = (res.headers.get('X-Datos-Ejemplo') || '').split(',').map((x) => x.trim()).filter(Boolean);
      setVista({ url: URL.createObjectURL(await res.blob()), ejemplo, formato });
    } catch (e) { toast.error(e.message); } finally { setTrabajando(''); }
  };
  const guardar = async () => {
    setTrabajando('guardar');
    try {
      await api('/fiscal/cuenta/kude', { method: 'PUT', body: JSON.stringify(diseno) });
      toast.success('Diseño del KuDE guardado en SIFEN SIS');
    } catch (e) { toast.error(e.message); } finally { setTrabajando(''); }
  };
  const subirLogo = async (archivo) => {
    if (!archivo) return;
    const datos = new FormData();
    datos.append('archivo', archivo);
    setTrabajando('logo');
    try {
      await conToken('/fiscal/cuenta/kude/logo', { method: 'POST', body: datos });
      toast.success('Logo subido');
      cargarLogo();
    } catch (e) { toast.error(e.message); } finally { setTrabajando(''); }
  };
  const quitarLogo = async () => {
    if (!window.confirm('¿Quitar el logo del KuDE?')) return;
    try {
      await api('/fiscal/cuenta/kude/logo', { method: 'DELETE' });
      setLogo(null);
    } catch (e) { toast.error(e.message); }
  };

  const color = (clave, etiqueta) => (
    <label className="flex items-center gap-2 text-sm">
      <input type="color" value={diseno[clave]} onChange={(e) => setDiseno({ ...diseno, [clave]: e.target.value.toUpperCase() })}
             className="h-8 w-10 cursor-pointer rounded border" />
      {etiqueta}
    </label>
  );
  const casilla = (clave, etiqueta) => (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={diseno[clave]} onChange={(e) => setDiseno({ ...diseno, [clave]: e.target.checked })} />
      {etiqueta}
    </label>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div className="flex h-16 w-28 items-center justify-center rounded-md border bg-white">
          {logo ? <img src={logo} alt="Logo del KuDE" className="max-h-14 max-w-24 object-contain" /> : <span className="text-xs text-muted-foreground">Sin logo</span>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" asChild>
            <label className="cursor-pointer">
              {trabajando === 'logo' ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}Subir logo
              <input type="file" accept="image/png,image/jpeg" className="hidden" data-testid="kude-logo"
                     onChange={(e) => { subirLogo(e.target.files?.[0]); e.target.value = ''; }} />
            </label>
          </Button>
          {logo && <Button size="sm" variant="ghost" className="text-destructive" onClick={quitarLogo}><Trash2 className="h-4 w-4 mr-1" />Quitar</Button>}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {color('colorPrimario', 'Color principal')}
        {color('colorSecundario', 'Color de fondo de las tablas')}
        {color('colorAcento', 'Color de acento')}
        {color('colorTexto', 'Color del texto')}
        {casilla('mostrarQr', 'Mostrar el código QR')}
        {casilla('mostrarTimbrado', 'Mostrar el timbrado')}
        {casilla('mostrarLiquidacion', 'Mostrar la liquidación del IVA')}
        {casilla('esquinasRedondeadas', 'Esquinas redondeadas')}
        <label className="flex items-center gap-2 text-sm">
          Tamaño del logo
          <select value={diseno.tamanoLogo} onChange={(e) => setDiseno({ ...diseno, tamanoLogo: e.target.value })}
                  className="h-8 rounded-md border border-input bg-transparent px-2">
            <option value="s">Chico</option><option value="m">Mediano</option><option value="l">Grande</option>
          </select>
        </label>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="kude-pie">Texto al pie</Label>
        <Input id="kude-pie" maxLength={300} value={diseno.textoPie} placeholder="Ej.: Gracias por su compra"
               onChange={(e) => setDiseno({ ...diseno, textoPie: e.target.value })} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={() => verVista('a4')} disabled={!!trabajando} data-testid="kude-vista-a4">
          {trabajando === 'vista-a4' ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Eye className="h-4 w-4 mr-1" />}Vista previa A4
        </Button>
        <Button size="sm" variant="outline" onClick={() => verVista('ticket')} disabled={!!trabajando}>
          {trabajando === 'vista-ticket' ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Eye className="h-4 w-4 mr-1" />}Vista previa ticket
        </Button>
        <Button size="sm" onClick={guardar} disabled={!!trabajando} data-testid="kude-guardar">
          {trabajando === 'guardar' ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}Guardar diseño
        </Button>
      </div>
      {vista && (
        <div className="space-y-2">
          {vista.ejemplo.length > 0 && (
            <p className="flex items-center gap-1 text-sm text-amber-700">
              <AlertTriangle className="h-4 w-4" />
              Falta cargar en SIFEN SIS: {vista.ejemplo.map((x) => DATOS_EJEMPLO[x] || x).join(', ')} (la vista previa los completa con datos de ejemplo).
            </p>
          )}
          <iframe title="Vista previa del KuDE" src={vista.url} data-testid="kude-vista"
                  className={`w-full rounded-md border ${vista.formato === 'a4' ? 'h-[600px]' : 'h-[500px]'}`} />
        </div>
      )}
    </div>
  );
}

function Certificado({ cuenta, alCambiar }) {
  const conToken = useConToken();
  const [archivo, setArchivo] = useState(null);
  const [clave, setClave] = useState('');
  const [subiendo, setSubiendo] = useState(false);
  const cert = cuenta.certificado || {};

  const subir = async (e) => {
    e.preventDefault();
    if (!window.confirm('El certificado nuevo reemplaza al actual: desde ahora las facturas se firman con él. ¿Seguir?')) return;
    const datos = new FormData();
    datos.append('archivo', archivo);
    datos.append('password', clave);
    setSubiendo(true);
    try {
      const vigente = await (await conToken('/fiscal/cuenta/certificado', { method: 'POST', body: datos })).json();
      toast.success(`Certificado cargado: vigente hasta ${fecha(vigente.validoHasta)}`);
      setArchivo(null);
      setClave('');
      alCambiar();
    } catch (err) { toast.error(err.message); } finally { setSubiendo(false); }
  };

  return (
    <form onSubmit={subir} className="space-y-3 text-sm">
      <p><BadgeCheck className="inline h-4 w-4 mr-1" />Actual: {cert.vigente ? `vigente hasta ${fecha(cert.validoHasta)} (${cert.diasParaVencer} días)` : 'no vigente o sin cargar'}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="cert-archivo">Archivo .p12 o .pfx</Label>
          <Input id="cert-archivo" type="file" accept=".p12,.pfx" required onChange={(e) => setArchivo(e.target.files?.[0] || null)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="cert-clave">Contraseña del certificado</Label>
          <Input id="cert-clave" type="password" autoComplete="off" required value={clave} onChange={(e) => setClave(e.target.value)} />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">Se envía a SIFEN SIS, que firma las facturas. El ERP no guarda ni el archivo ni la contraseña.</p>
      <Button size="sm" type="submit" disabled={subiendo || !archivo}>
        {subiendo ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Upload className="h-4 w-4 mr-1" />}Subir certificado
      </Button>
    </form>
  );
}

function Correo({ configuracion }) {
  const { api } = useApp();
  const c = configuracion.correo || {};
  const [datos, setDatos] = useState({ envioActivo: !!c.envioActivo, nombreRemitente: c.nombreRemitente || '',
                                       responderA: c.responderA || '', adjuntarXml: !!c.adjuntarXml, enviarEnPruebas: !!c.enviarEnPruebas });
  const [destino, setDestino] = useState('');
  const [trabajando, setTrabajando] = useState('');

  const guardar = async () => {
    setTrabajando('guardar');
    try {
      await api('/fiscal/cuenta/correo', { method: 'PUT', body: JSON.stringify(datos) });
      toast.success('Envío por correo guardado');
    } catch (e) { toast.error(e.message); } finally { setTrabajando(''); }
  };
  const probar = async () => {
    setTrabajando('probar');
    try {
      await api('/fiscal/cuenta/correo/prueba', { method: 'POST', body: JSON.stringify({ destino }) });
      toast.success(`Correo de prueba enviado a ${destino}`);
    } catch (e) { toast.error(e.message); } finally { setTrabajando(''); }
  };
  const casilla = (clave, etiqueta) => (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={datos[clave]} onChange={(e) => setDatos({ ...datos, [clave]: e.target.checked })} />
      {etiqueta}
    </label>
  );

  return (
    <div className="space-y-3">
      {casilla('envioActivo', 'Enviar la factura al cliente por correo (al e-mail cargado en su ficha)')}
      {casilla('adjuntarXml', 'Adjuntar también el XML')}
      {casilla('enviarEnPruebas', 'Enviar también en pruebas (SANDBOX / HOMOLOGACION)')}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5"><Label htmlFor="correo-nombre">Nombre del remitente</Label>
          <Input id="correo-nombre" value={datos.nombreRemitente} onChange={(e) => setDatos({ ...datos, nombreRemitente: e.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor="correo-responder">Responder a</Label>
          <Input id="correo-responder" type="email" value={datos.responderA} onChange={(e) => setDatos({ ...datos, responderA: e.target.value })} /></div>
      </div>
      <Button size="sm" onClick={guardar} disabled={!!trabajando}>
        {trabajando === 'guardar' ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}Guardar
      </Button>
      <div className="flex flex-wrap items-end gap-2 border-t pt-3">
        <div className="space-y-1.5 flex-1 min-w-[14rem]"><Label htmlFor="correo-prueba">Mandar un correo de prueba a</Label>
          <Input id="correo-prueba" type="email" value={destino} onChange={(e) => setDestino(e.target.value)} /></div>
        <Button size="sm" variant="outline" onClick={probar} disabled={!!trabajando || !destino}>
          {trabajando === 'probar' ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Mail className="h-4 w-4 mr-1" />}Enviar prueba
        </Button>
      </div>
    </div>
  );
}

function Timbrado({ configuracion, alCambiar }) {
  const { api } = useApp();
  const [datos, setDatos] = useState({ ambiente: 'PRODUCCION', numero: '', fecha_inicio: '' });
  const [guardando, setGuardando] = useState(false);
  const guardar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    try {
      await api('/fiscal/cuenta/timbrado', { method: 'PUT', body: JSON.stringify(datos) });
      toast.success('Timbrado guardado');
      alCambiar();
    } catch (err) { toast.error(err.message); } finally { setGuardando(false); }
  };
  return (
    <form onSubmit={guardar} className="space-y-3 text-sm">
      <ul className="space-y-1">
        {(configuracion.timbrados || []).map((t) => (
          <li key={t.ambiente}><Badge variant="outline">{t.ambiente}</Badge> N° {t.numero} desde {fecha(t.fechaInicio)}</li>
        ))}
      </ul>
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="space-y-1.5"><Label htmlFor="timbrado-ambiente">Ambiente</Label>
          <select id="timbrado-ambiente" value={datos.ambiente} onChange={(e) => setDatos({ ...datos, ambiente: e.target.value })}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm">
            <option value="PRODUCCION">Producción</option><option value="HOMOLOGACION">Homologación (pruebas)</option>
          </select></div>
        <div className="space-y-1.5"><Label htmlFor="timbrado-numero">Número (8 dígitos)</Label>
          <Input id="timbrado-numero" required pattern="\d{8}" value={datos.numero} onChange={(e) => setDatos({ ...datos, numero: e.target.value })} /></div>
        <div className="space-y-1.5"><Label htmlFor="timbrado-fecha">Inicio de vigencia</Label>
          <Input id="timbrado-fecha" type="date" required value={datos.fecha_inicio} onChange={(e) => setDatos({ ...datos, fecha_inicio: e.target.value })} /></div>
      </div>
      <Button size="sm" type="submit" disabled={guardando}>
        {guardando ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Save className="h-4 w-4 mr-1" />}Guardar timbrado
      </Button>
    </form>
  );
}

export default function CuentaSifenSis() {
  const { api } = useApp();
  const [estado, setEstado] = useState(undefined); // undefined cargando; { error } o la respuesta
  const cargar = useCallback(() => {
    api('/fiscal/cuenta').then(setEstado).catch((e) => setEstado({ error: e.message }));
  }, [api]);
  useEffect(() => { cargar(); }, [cargar]);

  return (
    <Card data-testid="cuenta-sifensis">
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-5 w-5" />Cuenta de SIFEN SIS</CardTitle>
        <CardDescription>Estado de la cuenta, certificado, diseño del KuDE, envío por correo y timbrado, sin entrar al portal.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {estado === undefined && <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />}
        {estado?.error && <p className="text-sm text-muted-foreground">{estado.error}</p>}
        {estado?.cuenta && <Estado cuenta={estado.cuenta} />}
        {estado?.cuenta && !estado.permiso_configuracion && (
          <div className="flex gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"
               data-testid="sin-permiso-configuracion">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <p>La API key cargada sólo emite. Para cambiar desde acá el certificado, el KuDE, el correo y el timbrado, generá en el
              portal de SIFEN SIS una key <b>"Emisión + configuración"</b> y cargala en Facturación electrónica.</p>
          </div>
        )}
        {estado?.configuracion && (
          <Tabs defaultValue="kude">
            <TabsList>
              <TabsTrigger value="kude">KuDE</TabsTrigger>
              <TabsTrigger value="certificado">Certificado</TabsTrigger>
              <TabsTrigger value="correo">Correo</TabsTrigger>
              <TabsTrigger value="timbrado">Timbrado</TabsTrigger>
            </TabsList>
            <TabsContent value="kude" className="pt-3"><Kude configuracion={estado.configuracion} /></TabsContent>
            <TabsContent value="certificado" className="pt-3"><Certificado cuenta={estado.cuenta} alCambiar={cargar} /></TabsContent>
            <TabsContent value="correo" className="pt-3"><Correo configuracion={estado.configuracion} /></TabsContent>
            <TabsContent value="timbrado" className="pt-3"><Timbrado configuracion={estado.configuracion} alCambiar={cargar} /></TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}
