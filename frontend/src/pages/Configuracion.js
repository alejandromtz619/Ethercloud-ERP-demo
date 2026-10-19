import React, { useCallback, useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  AlertTriangle, Building2, CheckCircle2, Copy, History, KeyRound, Loader2, Lock, Plug, Puzzle, Save, XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { resolverImagenUrl } from '../lib/imagenes';
import { olvidarAjustesImpresion } from '../lib/ajustesImpresion';
import CuentaSifenSis from '../components/CuentaSifenSis';
import { useModulos } from '../lib/modulos';

// Configuración de esta instancia: lo que cambia de un cliente a otro (datos de la empresa, claves de
// APIs, conexiones). Las secciones vienen del backend (backend/configuracion.py): una clave nueva
// aparece acá sin tocar esta pantalla.

const fechaHora = (iso) => (iso ? new Date(iso).toLocaleString('es-PY', { timeZone: 'America/Asuncion' }) : '—');

const NOMBRES_MODULOS = {
  fe: 'Facturación electrónica',
  crm: 'CRM',
  crm_ia: 'Inteligencia artificial del CRM',
  crm_ads: 'Publicidad (Meta Ads)',
};

const PERFILES_TOKEN = {
  'crm-interno': 'CRM (lectura completa y pedidos)',
  'crm-bot': 'Bot (sólo catálogo y pedidos)',
};

// ---------------------------------------------------------------- empresa

function DatosEmpresa() {
  const { api, empresa, setEmpresa } = useApp();
  const [datos, setDatos] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [logoError, setLogoError] = useState(false);

  useEffect(() => {
    if (empresa) {
      setDatos({
        nombre: empresa.nombre || '', ruc: empresa.ruc || '', direccion: empresa.direccion || '',
        telefono: empresa.telefono || '', email: empresa.email || '', logo_url: empresa.logo_url || '',
      });
    }
  }, [empresa]);

  if (!datos) return null;
  const campo = (clave, etiqueta, extra = {}) => (
    <div className="space-y-1.5">
      <Label htmlFor={`empresa-${clave}`}>{etiqueta}</Label>
      <Input id={`empresa-${clave}`} value={datos[clave]} data-testid={`empresa-${clave}`}
             onChange={(e) => setDatos({ ...datos, [clave]: e.target.value })} {...extra} />
    </div>
  );

  const guardar = async () => {
    setGuardando(true);
    try {
      const actualizada = await api(`/empresas/${empresa.id}`, {
        method: 'PUT',
        body: JSON.stringify({ ...datos, logo_url: datos.logo_url.trim() || null }),
      });
      setEmpresa(actualizada);
      toast.success('Datos de la empresa guardados');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <Card data-testid="tarjeta-empresa">
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Building2 className="h-5 w-5" />Empresa</CardTitle>
        <CardDescription>Aparecen en el login, el menú y los documentos impresos.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          {campo('nombre', 'Razón social')}
          {campo('ruc', 'RUC', { placeholder: '80012345-6' })}
          {campo('direccion', 'Dirección')}
          {campo('telefono', 'Teléfono')}
          {campo('email', 'E-mail', { type: 'email' })}
        </div>
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl bg-primary flex items-center justify-center overflow-hidden shrink-0">
            {datos.logo_url && !logoError ? (
              <img src={resolverImagenUrl(datos.logo_url)} alt="Logo" className="w-full h-full object-contain p-1"
                   onError={() => setLogoError(true)} />
            ) : (
              <span className="text-xl font-bold text-white">{(datos.nombre || '?').substring(0, 2).toUpperCase()}</span>
            )}
          </div>
          <div className="flex-1 space-y-1.5">
            <Label htmlFor="empresa-logo_url">URL del logo</Label>
            <Input id="empresa-logo_url" className="font-mono text-xs" value={datos.logo_url}
                   placeholder="https://…/logo.png"
                   onChange={(e) => { setDatos({ ...datos, logo_url: e.target.value }); setLogoError(false); }} />
          </div>
        </div>
        <Button onClick={guardar} disabled={guardando} data-testid="guardar-empresa">
          {guardando ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}Guardar
        </Button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------- secciones de configuración

function Campo({ campo, valor, onCambio, secreto, onSecreto, borrar, onBorrar }) {
  const bloqueado = !campo.editable;
  return (
    <div className="space-y-1.5" data-testid={`campo-${campo.clave}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <Label htmlFor={campo.clave}>{campo.etiqueta}</Label>
        {campo.origen === 'entorno' && (
          <Badge variant="secondary" className="gap-1"><Lock className="h-3 w-3" />Fijado en el servidor</Badge>
        )}
      </div>
      {campo.secreta ? (
        <>
          {campo.ilegible && (
            <p className="text-sm text-destructive">No se puede leer: cambió la clave de cifrado del servidor. Volvé a cargarla.</p>
          )}
          {campo.configurado && !borrar && (
            <p className="text-sm text-muted-foreground">
              Cargada (termina en <span className="font-mono">{campo.termina_en}</span>)
              {campo.editable && <button type="button" className="ml-2 text-destructive underline" onClick={() => onBorrar(true)}>Quitar</button>}
            </p>
          )}
          {borrar && (
            <p className="text-sm text-destructive">
              Se va a quitar al guardar. <button type="button" className="underline" onClick={() => onBorrar(false)}>Deshacer</button>
            </p>
          )}
          {!bloqueado && !borrar && (
            <Input id={campo.clave} type="password" autoComplete="new-password" value={secreto}
                   placeholder={campo.configurado ? 'Pegá una nueva para reemplazarla' : 'Pegala acá'}
                   onChange={(e) => onSecreto(e.target.value)} />
          )}
        </>
      ) : campo.tipo === 'opcion' ? (
        <select id={campo.clave} value={valor} disabled={bloqueado} onChange={(e) => onCambio(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm disabled:opacity-50">
          {campo.opciones.map((o) => <option key={o.valor} value={o.valor}>{o.etiqueta}</option>)}
        </select>
      ) : (
        <Input id={campo.clave} value={valor} disabled={bloqueado} inputMode={campo.tipo === 'decimal' ? 'decimal' : undefined}
               onChange={(e) => onCambio(e.target.value)} />
      )}
      {campo.ayuda && <p className="text-xs text-muted-foreground">{campo.ayuda}</p>}
    </div>
  );
}

const valorInicial = (campo) => (campo.valor === null || campo.valor === undefined ? '' : String(campo.valor));

function Seccion({ seccion, onGuardado }) {
  const { api } = useApp();
  const [campos, setCampos] = useState(seccion.campos);
  const [valores, setValores] = useState({});
  const [secretos, setSecretos] = useState({});
  const [borrar, setBorrar] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [probando, setProbando] = useState(false);
  const [prueba, setPrueba] = useState(null);

  const reiniciar = useCallback((lista) => {
    setCampos(lista);
    setValores(Object.fromEntries(lista.filter((c) => !c.secreta).map((c) => [c.clave, valorInicial(c)])));
    setSecretos({});
    setBorrar({});
  }, []);
  useEffect(() => { reiniciar(seccion.campos); }, [seccion, reiniciar]);

  const cambios = {};
  campos.forEach((c) => {
    if (!c.editable) return;
    if (c.secreta) {
      if (borrar[c.clave]) cambios[c.clave] = null;
      else if ((secretos[c.clave] || '').trim()) cambios[c.clave] = secretos[c.clave].trim();
    } else if ((valores[c.clave] ?? '') !== valorInicial(c)) {
      cambios[c.clave] = valores[c.clave];
    }
  });
  const hayCambios = Object.keys(cambios).length > 0;
  const editable = campos.some((c) => c.editable);

  const guardar = async () => {
    setGuardando(true);
    try {
      const r = await api(`/configuracion/${seccion.seccion}`, { method: 'PUT', body: JSON.stringify({ valores: cambios }) });
      reiniciar(r.campos);
      setPrueba(null);
      if (seccion.seccion === 'documentos') olvidarAjustesImpresion();
      toast.success('Guardado');
      onGuardado();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setGuardando(false);
    }
  };

  const probar = async () => {
    setProbando(true);
    try {
      setPrueba(await api(`/configuracion/${seccion.seccion}/probar`, { method: 'POST' }));
    } catch (e) {
      setPrueba({ ok: false, error: e.message });
    } finally {
      setProbando(false);
    }
  };

  return (
    <Card data-testid={`seccion-${seccion.seccion}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5" />{seccion.titulo}</CardTitle>
        {!editable && <CardDescription>Sólo lectura con tus permisos.</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          {campos.map((c) => (
            <div key={c.clave} className={c.secreta || c.tipo === 'opcion' ? 'sm:col-span-2' : ''}>
              <Campo campo={c} valor={valores[c.clave] ?? ''} onCambio={(v) => setValores({ ...valores, [c.clave]: v })}
                     secreto={secretos[c.clave] || ''} onSecreto={(v) => setSecretos({ ...secretos, [c.clave]: v })}
                     borrar={!!borrar[c.clave]} onBorrar={(b) => setBorrar({ ...borrar, [c.clave]: b })} />
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {editable && (
            <Button onClick={guardar} disabled={!hayCambios || guardando} data-testid={`guardar-${seccion.seccion}`}>
              {guardando ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}Guardar
            </Button>
          )}
          {seccion.se_puede_probar && (
            <Button variant="outline" onClick={probar} disabled={probando || hayCambios} data-testid={`probar-${seccion.seccion}`}
                    title={hayCambios ? 'Guardá los cambios antes de probar' : undefined}>
              {probando ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plug className="h-4 w-4 mr-2" />}Probar conexión
            </Button>
          )}
        </div>
        {prueba && (
          <div className={`rounded-md border p-3 text-sm ${prueba.ok ? 'border-green-300 bg-green-50 dark:bg-green-950/30' : 'border-destructive/40 bg-destructive/5'}`}
               data-testid={`resultado-${seccion.seccion}`}>
            {prueba.ok ? (
              <>
                <p className="flex items-center gap-2 font-medium text-green-700 dark:text-green-400"><CheckCircle2 className="h-4 w-4" />Conexión correcta</p>
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                  {Object.entries(prueba).filter(([k]) => k !== 'ok').map(([k, v]) => (
                    <React.Fragment key={k}>
                      <dt className="text-muted-foreground capitalize">{k.replace(/_/g, ' ')}</dt>
                      <dd className="font-medium">{Array.isArray(v) ? v.join(', ') : String(v ?? '—')}</dd>
                    </React.Fragment>
                  ))}
                </dl>
              </>
            ) : (
              <p className="flex items-center gap-2 text-destructive"><XCircle className="h-4 w-4" />{prueba.error}</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------- tokens de integración

function TokensIntegracion() {
  const { api } = useApp();
  const [tokens, setTokens] = useState([]);
  const [nombre, setNombre] = useState('');
  const [perfil, setPerfil] = useState('crm-interno');
  const [creando, setCreando] = useState(false);
  const [nuevo, setNuevo] = useState(null);

  const cargar = useCallback(() => api('/integracion/tokens').then(setTokens).catch((e) => toast.error(e.message)), [api]);
  useEffect(() => { cargar(); }, [cargar]);

  const crear = async (e) => {
    e.preventDefault();
    setCreando(true);
    try {
      setNuevo(await api('/integracion/tokens', { method: 'POST', body: JSON.stringify({ nombre, perfil }) }));
      setNombre('');
      cargar();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreando(false);
    }
  };

  const revocar = async (t) => {
    if (!window.confirm(`¿Revocar el token "${t.nombre}"? El servicio que lo usa deja de funcionar.`)) return;
    try {
      await api(`/integracion/tokens/${t.id}`, { method: 'DELETE' });
      cargar();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(nuevo.token);
      toast.success('Copiado');
    } catch {
      toast.error('No se pudo copiar: seleccionalo y copialo a mano');
    }
  };

  return (
    <Card data-testid="tarjeta-tokens">
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Plug className="h-5 w-5" />Tokens de integración</CardTitle>
        <CardDescription>Credenciales con las que otros servicios (CRM, bot) leen el ERP. Cada token se muestra una sola vez.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="divide-y rounded-md border">
          {tokens.length === 0 && <p className="p-3 text-sm text-muted-foreground">Todavía no hay tokens.</p>}
          {tokens.map((t) => (
            <div key={t.id} className="flex items-center gap-3 p-3 text-sm">
              <div className="flex-1 min-w-0">
                <p className="font-medium truncate">{t.nombre} <span className="font-mono text-xs text-muted-foreground">{t.prefijo}…</span></p>
                <p className="text-xs text-muted-foreground">
                  {t.scopes?.includes('clientes.leer') ? PERFILES_TOKEN['crm-interno'] : PERFILES_TOKEN['crm-bot']} · creado {fechaHora(t.creado_en)} · último uso {fechaHora(t.ultimo_uso)}
                </p>
              </div>
              {t.activo
                ? <Button size="sm" variant="ghost" className="text-destructive" onClick={() => revocar(t)}>Revocar</Button>
                : <Badge variant="outline">Revocado</Badge>}
            </div>
          ))}
        </div>
        <form onSubmit={crear} className="flex flex-wrap gap-2 items-end">
          <div className="space-y-1.5 flex-1 min-w-[12rem]">
            <Label htmlFor="token-nombre">Nombre</Label>
            <Input id="token-nombre" required maxLength={100} placeholder="Ej.: CRM" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </div>
          <div className="space-y-1.5 w-72">
            <Label>Tipo</Label>
            <Select value={perfil} onValueChange={setPerfil}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(PERFILES_TOKEN).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" disabled={creando}>{creando && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Crear token</Button>
        </form>
      </CardContent>
      <Dialog open={!!nuevo} onOpenChange={(abierto) => !abierto && setNuevo(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Token "{nuevo?.nombre}"</DialogTitle>
            <DialogDescription>Copialo ahora y pegalo en el servicio que lo va a usar. Después no se puede volver a ver.</DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-muted p-3 font-mono text-xs break-all" data-testid="token-nuevo">{nuevo?.token}</div>
          <DialogFooter>
            <Button variant="outline" onClick={copiar}><Copy className="h-4 w-4 mr-2" />Copiar</Button>
            <Button onClick={() => setNuevo(null)}>Listo</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// ---------------------------------------------------------------- módulos e historial

function Modulos() {
  const { api } = useApp();
  const [modulos, setModulos] = useState({});
  useEffect(() => { api('/sistema/modulos').then(setModulos).catch(() => {}); }, [api]);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Puzzle className="h-5 w-5" />Módulos</CardTitle>
        <CardDescription>Los habilita Ether según lo contratado.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        {Object.entries(NOMBRES_MODULOS).map(([clave, nombre]) => (
          <Badge key={clave} variant={modulos[clave] ? 'default' : 'outline'}>
            {nombre}: {modulos[clave] ? 'activo' : 'no contratado'}
          </Badge>
        ))}
      </CardContent>
    </Card>
  );
}

function Historial({ version }) {
  const { api } = useApp();
  const [cambios, setCambios] = useState([]);
  useEffect(() => { api('/configuracion/cambios?limit=20').then(setCambios).catch(() => {}); }, [api, version]);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><History className="h-5 w-5" />Últimos cambios</CardTitle>
      </CardHeader>
      <CardContent>
        {cambios.length === 0 ? <p className="text-sm text-muted-foreground">Sin cambios registrados.</p> : (
          <ul className="space-y-2 text-sm" data-testid="historial-configuracion">
            {cambios.map((c, i) => (
              <li key={i} className="flex flex-wrap gap-x-2">
                <span className="text-muted-foreground">{fechaHora(c.creado_en)} · {c.usuario || 'sistema'}</span>
                <span className="font-medium">{c.etiqueta}:</span>
                {c.clave.startsWith('sifensis.')
                  ? <span>{c.valor_nuevo}</span>
                  : <span>{c.valor_anterior || '(vacío)'} → {c.valor_nuevo === null ? '(por defecto)' : (c.valor_nuevo || '(vacío)')}</span>}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------- página

const Configuracion = () => {
  const { api, hasPermission } = useApp();
  const [config, setConfig] = useState(null);
  const [version, setVersion] = useState(0);
  const modulos = useModulos();

  const cargar = useCallback(() => api('/configuracion').then(setConfig).catch((e) => toast.error(e.message)), [api]);
  useEffect(() => { cargar(); }, [cargar]);
  const alGuardar = () => setVersion((v) => v + 1);

  return (
    <div className="space-y-6 max-w-3xl" data-testid="configuracion-page">
      <div>
        <h1 className="text-2xl font-bold">Configuración</h1>
        <p className="text-muted-foreground">Datos de esta empresa y conexiones con otros servicios. Se guardan en el sistema, sin tocar el servidor.</p>
      </div>
      {config && !config.cifrado_disponible && (
        <div className="flex gap-3 rounded-md border border-yellow-300 bg-yellow-50 p-3 text-sm dark:bg-yellow-950/30">
          <AlertTriangle className="h-5 w-5 text-yellow-600 shrink-0" />
          <p>Falta la clave de cifrado del servidor (<span className="font-mono">CLAVE_CIFRADO</span>): no se pueden guardar API keys. Pedíselo a soporte de Ether.</p>
        </div>
      )}
      {hasPermission('sistema.configurar') && <DatosEmpresa />}
      {config?.secciones.map((s) => <Seccion key={s.seccion} seccion={s} onGuardado={alGuardar} />)}
      {hasPermission('sistema.integraciones') && modulos.fe && <CuentaSifenSis key={version} />}
      {hasPermission('sistema.integraciones') && <TokensIntegracion />}
      <Modulos />
      <Historial version={version} />
    </div>
  );
};

export default Configuracion;
