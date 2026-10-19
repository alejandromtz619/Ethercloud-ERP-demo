import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { useModulos } from '../lib/modulos';

// Datos del cliente para la factura electrónica (sólo con el módulo fe). Todo opcional: sin domicilio
// completo la factura sale sin dirección del receptor. Los códigos son los de los catálogos de SIFEN.
export const CAMPOS_FISCALES = ['tipo_contribuyente', 'tipo_operacion', 'numero_casa', 'departamento', 'distrito', 'ciudad'];

// Para el formulario: null -> ''
export const fiscalesDesde = (cliente) =>
  Object.fromEntries(CAMPOS_FISCALES.map((c) => [c, cliente?.[c] ?? '']));

// Para la API: '' -> null y números
export const fiscalesParaEnviar = (datos) =>
  Object.fromEntries(CAMPOS_FISCALES.map((c) => [c, datos[c] === '' || datos[c] === null || datos[c] === undefined ? null : Number(datos[c])]));

const clasesSelect = 'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring';

export default function DatosFiscalesCliente({ valor, onCambio }) {
  const { api } = useApp();
  const modulos = useModulos();
  const [departamentos, setDepartamentos] = useState([]);
  const [distritos, setDistritos] = useState([]);
  const [ciudades, setCiudades] = useState([]);

  useEffect(() => {
    if (modulos.fe) api('/fiscal/catalogos').then((c) => setDepartamentos(c.departamentos)).catch(() => {});
  }, [api, modulos.fe]);
  useEffect(() => {
    if (!modulos.fe || !valor.departamento) { setDistritos([]); return; }
    api(`/fiscal/catalogos/distritos?departamento=${valor.departamento}`).then(setDistritos).catch(() => {});
  }, [api, modulos.fe, valor.departamento]);
  useEffect(() => {
    if (!modulos.fe || !valor.distrito) { setCiudades([]); return; }
    api(`/fiscal/catalogos/ciudades?distrito=${valor.distrito}`).then(setCiudades).catch(() => {});
  }, [api, modulos.fe, valor.distrito]);

  if (!modulos.fe) return null;
  const select = (clave, etiqueta, opciones, extra = {}) => (
    <div className="space-y-1.5">
      <Label htmlFor={`fiscal-${clave}`}>{etiqueta}</Label>
      <select id={`fiscal-${clave}`} className={clasesSelect} value={valor[clave]} data-testid={`fiscal-${clave}`}
              onChange={(e) => onCambio({ [clave]: e.target.value, ...(extra.limpia || {}) })} disabled={extra.disabled}>
        <option value="">{extra.vacio || '—'}</option>
        {opciones.map((o) => <option key={o.codigo} value={o.codigo}>{o.nombre}</option>)}
      </select>
    </div>
  );

  return (
    <fieldset className="space-y-3 rounded-md border p-3" data-testid="datos-fiscales">
      <legend className="px-1 text-sm font-medium">Factura electrónica</legend>
      <div className="grid grid-cols-2 gap-3">
        {select('tipo_contribuyente', 'Tipo de contribuyente',
                [{ codigo: 1, nombre: 'Persona física' }, { codigo: 2, nombre: 'Persona jurídica' }], { vacio: 'Según el RUC' })}
        {select('tipo_operacion', 'Tipo de operación',
                [{ codigo: 1, nombre: 'B2B (empresa)' }, { codigo: 2, nombre: 'B2C (consumidor)' },
                 { codigo: 3, nombre: 'B2G (Estado)' }, { codigo: 4, nombre: 'B2F (exterior)' }], { vacio: 'Automático' })}
        {select('departamento', 'Departamento', departamentos, { limpia: { distrito: '', ciudad: '' } })}
        {select('distrito', 'Distrito', distritos, { limpia: { ciudad: '' }, disabled: !valor.departamento })}
        {select('ciudad', 'Ciudad', ciudades, { disabled: !valor.distrito })}
        <div className="space-y-1.5">
          <Label htmlFor="fiscal-numero_casa">Número de casa</Label>
          <Input id="fiscal-numero_casa" type="number" min="0" value={valor.numero_casa}
                 onChange={(e) => onCambio({ numero_casa: e.target.value })} placeholder="0 si no tiene" />
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Con dirección, departamento, distrito y ciudad la factura lleva el domicilio del cliente; si falta alguno, sale sin él.
      </p>
    </fieldset>
  );
}
