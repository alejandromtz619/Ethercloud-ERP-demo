import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, ComposedChart, Area,
} from 'recharts';
import {
  TrendingUp, TrendingDown, Minus, ShoppingCart, Package, DollarSign,
  Users, AlertTriangle, ArrowUpRight, ArrowDownRight, RefreshCw,
  ShoppingBag, Loader2, Target, BoxesIcon, BarChart2, Lightbulb,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';

const formatPYG = (value) => {
  if (value === null || value === undefined) return '₲ 0';
  return `₲ ${Math.round(value).toLocaleString('es-PY')}`;
};

const formatNum = (value) => {
  if (value === null || value === undefined) return '0';
  return Number(value).toLocaleString('es-PY');
};

const CHART_COLORS = ['#0044CC', '#FF6B00', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f43f5e'];

const VariacionBadge = ({ pct }) => {
  if (pct === null || pct === undefined) return null;
  if (pct > 0) return (
    <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1">
      <ArrowUpRight className="h-3 w-3" /> +{pct}%
    </Badge>
  );
  if (pct < 0) return (
    <Badge className="bg-red-100 text-red-700 border-red-200 gap-1">
      <ArrowDownRight className="h-3 w-3" /> {pct}%
    </Badge>
  );
  return (
    <Badge variant="outline" className="gap-1 text-muted-foreground">
      <Minus className="h-3 w-3" /> 0%
    </Badge>
  );
};

const UrgenciaBadge = ({ urgencia }) => {
  const map = {
    ALTA: 'bg-red-100 text-red-700 border-red-200',
    MEDIA: 'bg-amber-100 text-amber-700 border-amber-200',
    BAJA: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  };
  return <Badge className={cn('text-xs', map[urgencia] || '')}>{urgencia}</Badge>;
};

const KpiCard = ({ title, value, sub, icon: Icon, colorClass = 'text-primary', trend }) => (
  <Card>
    <CardContent className="pt-5">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{title}</p>
          <p className={cn('text-2xl font-extrabold font-mono tracking-tight', colorClass)}>{value}</p>
          {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
        </div>
        <div className={cn('p-2 rounded-lg bg-muted', colorClass)}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
      {trend !== undefined && <div className="mt-3"><VariacionBadge pct={trend} /></div>}
    </CardContent>
  </Card>
);

// ─────────────────────────────────────────────────────────────────────────────
// TAB 1 — Estadísticas de ventas por producto
// ─────────────────────────────────────────────────────────────────────────────
const TabEstadisticas = ({ empresa, API_URL, token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [periodo, setPeriodo] = useState('semanal');
  const [periodos, setPeriodos] = useState('8');
  const [metrica, setMetrica] = useState('ventas');

  const fetch = useCallback(async () => {
    if (!empresa) return;
    setLoading(true);
    try {
      const res = await window.fetch(
        `${API_URL}/bi/estadisticas-productos?empresa_id=${empresa.id}&periodo=${periodo}&periodos=${periodos}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Error al cargar estadísticas');
      setData(await res.json());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [empresa, API_URL, token, periodo, periodos]);

  useEffect(() => { fetch(); }, [fetch]);

  const top5 = data?.productos?.slice(0, 5) || [];
  const topBar = top5.map(p => ({
    name: p.producto_nombre.length > 20 ? p.producto_nombre.slice(0, 18) + '…' : p.producto_nombre,
    ventas: p.total_ventas,
    unidades: p.total_unidades,
    ganancia: p.ganancia_bruta,
  }));

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Período</Label>
              <Select value={periodo} onValueChange={setPeriodo}>
                <SelectTrigger className="w-36 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="semanal">Semanal</SelectItem>
                  <SelectItem value="mensual">Mensual</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Cantidad de períodos</Label>
              <Select value={periodos} onValueChange={setPeriodos}>
                <SelectTrigger className="w-24 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['4','6','8','12','16','24'].map(v => (
                    <SelectItem key={v} value={v}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Métrica del gráfico</Label>
              <Select value={metrica} onValueChange={setMetrica}>
                <SelectTrigger className="w-32 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ventas">Ventas (₲)</SelectItem>
                  <SelectItem value="unidades">Unidades</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" variant="outline" onClick={fetch} disabled={loading} className="h-8 gap-1">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Actualizar
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Cargando análisis…
        </div>
      ) : data ? (
        <>
          {/* Trend Chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Evolución de {periodo === 'semanal' ? 'ventas semanales' : 'ventas mensuales'}</CardTitle>
              <CardDescription className="text-xs">Últimos {periodos} {periodo === 'semanal' ? 'períodos semana' : 'meses'}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={data.tendencia}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={45} />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }}
                      formatter={(value, name) => [
                        name === 'ventas' ? formatPYG(value) : formatNum(value),
                        name === 'ventas' ? 'Ventas' : 'Unidades',
                      ]}
                    />
                    <Bar dataKey={metrica} fill="#0044CC" radius={[4, 4, 0, 0]} opacity={0.85} />
                    <Line type="monotone" dataKey={metrica} stroke="#FF6B00" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Top 5 Bar */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Top 5 productos — {metrica === 'ventas' ? 'Ingresos' : 'Unidades vendidas'}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topBar} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={130} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }}
                      formatter={(v) => [metrica === 'ventas' ? formatPYG(v) : formatNum(v)]}
                    />
                    <Bar dataKey={metrica} fill="#0044CC" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Product Table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Detalle por producto</CardTitle>
              <CardDescription className="text-xs">
                {periodo === 'semanal' ? 'Comparativa: esta semana vs. semana anterior' : 'Comparativa: este mes vs. mes anterior'}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">#</th>
                      <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Producto</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Ventas</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Unidades</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Ganancia</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Prom./per.</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Stock</th>
                      <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Variación</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.productos.map((p, idx) => (
                      <tr key={p.producto_id} className="hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-2 text-muted-foreground">{idx + 1}</td>
                        <td className="px-4 py-2 font-medium max-w-[180px] truncate">{p.producto_nombre}</td>
                        <td className="px-4 py-2 text-right font-mono">{formatPYG(p.total_ventas)}</td>
                        <td className="px-4 py-2 text-right font-mono">{formatNum(p.total_unidades)}</td>
                        <td className="px-4 py-2 text-right font-mono text-emerald-600">{formatPYG(p.ganancia_bruta)}</td>
                        <td className="px-4 py-2 text-right font-mono">{p.promedio_por_periodo}</td>
                        <td className="px-4 py-2 text-right font-mono">{formatNum(p.stock_actual)}</td>
                        <td className="px-4 py-2 text-center"><VariacionBadge pct={p.variacion_pct} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// TAB 2 — Estadísticas de cierre
// ─────────────────────────────────────────────────────────────────────────────
const TabCierre = ({ empresa, API_URL, token }) => {
  const today = new Date().toISOString().split('T')[0];
  const firstOfYear = `${new Date().getFullYear()}-01-01`;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [desde, setDesde] = useState(firstOfYear);
  const [hasta, setHasta] = useState(today);

  const fetch = useCallback(async () => {
    if (!empresa) return;
    setLoading(true);
    try {
      const res = await window.fetch(
        `${API_URL}/bi/cierre?empresa_id=${empresa.id}&fecha_desde=${desde}&fecha_hasta=${hasta}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Error al cargar cierre');
      setData(await res.json());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [empresa, API_URL, token, desde, hasta]);

  useEffect(() => { fetch(); }, [fetch]);

  const pieData = data ? [
    { name: 'Ganancia neta', value: Math.max(0, data.resumen.balance_neto) },
    { name: 'Costo mercadería', value: data.ventas.costo },
    { name: 'Salarios', value: data.salarios.total_pagado },
  ].filter(d => d.value > 0) : [];

  const balanceBar = data?.evolucion_mensual?.map(m => ({
    mes: m.mes,
    ventas: m.ventas,
    ganancia: m.ganancia,
    costo: m.costo,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Desde</Label>
              <Input type="date" value={desde} onChange={e => setDesde(e.target.value)} className="h-8 text-sm w-40" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hasta</Label>
              <Input type="date" value={hasta} onChange={e => setHasta(e.target.value)} className="h-8 text-sm w-40" />
            </div>
            <Button size="sm" variant="outline" onClick={fetch} disabled={loading} className="h-8 gap-1">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Calcular
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Calculando balance…
        </div>
      ) : data ? (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <KpiCard
              title="Ingresos totales"
              value={formatPYG(data.ventas.total)}
              sub={`${formatNum(data.ventas.cantidad)} ventas`}
              icon={TrendingUp}
              colorClass="text-emerald-600"
            />
            <KpiCard
              title="Ganancia bruta"
              value={formatPYG(data.ventas.ganancia)}
              sub={`Margen ${data.resumen.margen_bruto_pct}%`}
              icon={DollarSign}
              colorClass="text-blue-600"
            />
            <KpiCard
              title="Compras mercadería"
              value={formatPYG(data.compras_mercaderia.total)}
              sub={`${formatNum(data.compras_mercaderia.num_entradas)} entradas`}
              icon={ShoppingBag}
              colorClass="text-amber-600"
            />
            <KpiCard
              title="Salarios pagados"
              value={formatPYG(data.salarios.total_pagado)}
              sub={`${formatNum(data.salarios.num_ciclos)} ciclos`}
              icon={Users}
              colorClass="text-purple-600"
            />
          </div>

          {/* Balance summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="md:col-span-2">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Evolución mensual de ventas y ganancia</CardTitle>
              </CardHeader>
              <CardContent>
                {balanceBar.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-10">No hay datos en el rango seleccionado.</p>
                ) : (
                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={balanceBar}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="mes" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }}
                          formatter={(v, name) => [formatPYG(v), name === 'ventas' ? 'Ventas' : name === 'ganancia' ? 'Ganancia' : 'Costo']}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Bar dataKey="ventas" name="Ventas" fill="#0044CC" radius={[3, 3, 0, 0]} opacity={0.8} />
                        <Bar dataKey="ganancia" name="Ganancia" fill="#10b981" radius={[3, 3, 0, 0]} opacity={0.8} />
                        <Bar dataKey="costo" name="Costo venta" fill="#f59e0b" radius={[3, 3, 0, 0]} opacity={0.8} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Distribución de egresos</CardTitle>
              </CardHeader>
              <CardContent>
                {pieData.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-10">Sin datos.</p>
                ) : (
                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3}>
                          {pieData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                        </Pie>
                        <Tooltip formatter={(v) => formatPYG(v)} contentStyle={{ fontSize: '12px', borderRadius: '6px', border: '1px solid hsl(var(--border))' }} />
                        <Legend wrapperStyle={{ fontSize: '10px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Balance final */}
          <Card className={cn('border-2', data.resumen.balance_neto >= 0 ? 'border-emerald-500/30' : 'border-red-500/30')}>
            <CardContent className="pt-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground font-medium">Balance neto del período</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Ganancia bruta − Salarios pagados</p>
                </div>
                <p className={cn('text-3xl font-extrabold font-mono', data.resumen.balance_neto >= 0 ? 'text-emerald-600' : 'text-red-600')}>
                  {formatPYG(data.resumen.balance_neto)}
                </p>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-4 text-center border-t pt-4 border-border">
                <div>
                  <p className="text-xs text-muted-foreground">Total ingresos</p>
                  <p className="text-sm font-bold font-mono text-emerald-600">{formatPYG(data.resumen.total_ingresos)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Total egresos</p>
                  <p className="text-sm font-bold font-mono text-red-600">{formatPYG(data.resumen.total_egresos)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Deudas prov. pendientes</p>
                  <p className="text-sm font-bold font-mono text-amber-600">{formatPYG(data.deudas_pendientes.total)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// TAB 3 — Sugerencias de compra
// ─────────────────────────────────────────────────────────────────────────────
const TabSugerencias = ({ empresa, API_URL, token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [semanasAnalisis, setSemanasAnalisis] = useState('4');
  const [semanasCobertura, setSemanasCobertura] = useState('4');

  const fetch = useCallback(async () => {
    if (!empresa) return;
    setLoading(true);
    try {
      const res = await window.fetch(
        `${API_URL}/bi/sugerencias-compra?empresa_id=${empresa.id}&semanas_analisis=${semanasAnalisis}&semanas_cobertura=${semanasCobertura}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Error al cargar sugerencias');
      setData(await res.json());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [empresa, API_URL, token, semanasAnalisis, semanasCobertura]);

  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Semanas de análisis</Label>
              <Select value={semanasAnalisis} onValueChange={setSemanasAnalisis}>
                <SelectTrigger className="w-36 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['2','4','6','8','12'].map(v => <SelectItem key={v} value={v}>{v} semanas</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Cobertura objetivo</Label>
              <Select value={semanasCobertura} onValueChange={setSemanasCobertura}>
                <SelectTrigger className="w-36 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['1','2','3','4','6','8'].map(v => <SelectItem key={v} value={v}>{v} semanas</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" variant="outline" onClick={fetch} disabled={loading} className="h-8 gap-1">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Recalcular
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            Analiza las últimas <strong>{semanasAnalisis} semanas</strong> de ventas y recomienda stock para cubrir las próximas <strong>{semanasCobertura} semanas</strong>.
          </p>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Analizando velocidad de ventas…
        </div>
      ) : data ? (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <KpiCard title="Productos a comprar" value={formatNum(data.resumen.productos_con_necesidad)} icon={ShoppingCart} colorClass="text-primary" />
            <KpiCard title="Urgentes" value={formatNum(data.resumen.urgentes)} icon={AlertTriangle} colorClass="text-red-600" />
            <KpiCard title="Media urgencia" value={formatNum(data.resumen.media_urgencia)} icon={Target} colorClass="text-amber-600" />
            <KpiCard title="Costo total estimado" value={formatPYG(data.resumen.costo_total_estimado)} icon={DollarSign} colorClass="text-emerald-600" />
          </div>

          {/* Suggestion chart */}
          {data.sugerencias.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Cantidad sugerida de compra (top 12)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.sugerencias.slice(0, 12).map(s => ({
                      name: s.producto_nombre.length > 18 ? s.producto_nombre.slice(0, 16) + '…' : s.producto_nombre,
                      sugerida: s.compra_sugerida,
                      stock: s.stock_actual,
                    }))} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 10 }} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={130} />
                      <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }} />
                      <Legend wrapperStyle={{ fontSize: '11px' }} />
                      <Bar dataKey="stock" name="Stock actual" fill="#10b981" radius={[0, 3, 3, 0]} />
                      <Bar dataKey="sugerida" name="Compra sugerida" fill="#0044CC" radius={[0, 3, 3, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Listado de sugerencias</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {data.sugerencias.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-12">
                  ¡Excelente! No hay productos que requieran reposición con los parámetros actuales.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Producto</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Vel. semanal</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Stock actual</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Cobertura</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Stock obj.</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Compra sugerida</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Costo est.</th>
                        <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Urgencia</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {data.sugerencias.map(s => (
                        <tr key={s.producto_id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2 font-medium max-w-[180px] truncate">{s.producto_nombre}</td>
                          <td className="px-4 py-2 text-right font-mono">{s.velocidad_semanal} u/sem</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(s.stock_actual)}</td>
                          <td className="px-4 py-2 text-right font-mono text-muted-foreground">
                            {s.cobertura_actual_semanas !== null ? `${s.cobertura_actual_semanas} sem.` : '—'}
                          </td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(s.stock_recomendado)}</td>
                          <td className="px-4 py-2 text-right font-mono font-bold text-primary">{formatNum(s.compra_sugerida)}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatPYG(s.costo_estimado)}</td>
                          <td className="px-4 py-2 text-center"><UrgenciaBadge urgencia={s.urgencia} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// TAB 4 — Exceso de compras
// ─────────────────────────────────────────────────────────────────────────────
const TabExceso = ({ empresa, API_URL, token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [semanas, setSemanas] = useState('4');

  const fetch = useCallback(async () => {
    if (!empresa) return;
    setLoading(true);
    try {
      const res = await window.fetch(
        `${API_URL}/bi/exceso-compras?empresa_id=${empresa.id}&semanas_referencia=${semanas}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Error al cargar excesos');
      setData(await res.json());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [empresa, API_URL, token, semanas]);

  useEffect(() => { fetch(); }, [fetch]);

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Semanas de referencia</Label>
              <Select value={semanas} onValueChange={setSemanas}>
                <SelectTrigger className="w-36 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['2','4','6','8','12'].map(v => <SelectItem key={v} value={v}>{v} semanas</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" variant="outline" onClick={fetch} disabled={loading} className="h-8 gap-1">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Analizar
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            Identifica productos con stock que tardará más de <strong>{parseInt(semanas) * 2} semanas</strong> en agotarse según la velocidad de venta actual.
          </p>
        </CardContent>
      </Card>

      {loading ? (
        <div className="flex items-center justify-center h-48 text-muted-foreground gap-2">
          <Loader2 className="h-5 w-5 animate-spin" /> Analizando inventario…
        </div>
      ) : data ? (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KpiCard
              title="Productos con exceso"
              value={formatNum(data.resumen.productos_exceso)}
              icon={BoxesIcon}
              colorClass="text-amber-600"
            />
            <KpiCard
              title="Sin ventas recientes"
              value={formatNum(data.resumen.productos_sin_ventas)}
              icon={AlertTriangle}
              colorClass="text-red-600"
            />
            <KpiCard
              title="Capital inmovilizado total"
              value={formatPYG(data.resumen.valor_total_inmovilizado)}
              sub="Costo de stock sin salida"
              icon={DollarSign}
              colorClass="text-destructive"
            />
          </div>

          {/* Exceso de stock chart */}
          {data.exceso_stock.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold">Productos con exceso — Semanas para agotar (top 12)</CardTitle>
                <CardDescription className="text-xs">Cuanto mayor la barra, más tiempo lleva normalizar el stock</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.exceso_stock.slice(0, 12).map(e => ({
                      name: e.producto_nombre.length > 18 ? e.producto_nombre.slice(0, 16) + '…' : e.producto_nombre,
                      semanas: e.semanas_para_agotar,
                      stock: e.stock_actual,
                    }))} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 10 }} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={130} />
                      <Tooltip
                        contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }}
                        formatter={(v, name) => [name === 'semanas' ? `${v} sem.` : formatNum(v), name === 'semanas' ? 'Sem. para agotar' : 'Stock actual']}
                      />
                      <Legend wrapperStyle={{ fontSize: '11px' }} />
                      <Bar dataKey="semanas" name="Semanas para agotar" fill="#f59e0b" radius={[0, 3, 3, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Exceso table */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                Stock en exceso respecto a la venta
                {data.exceso_stock.length > 0 && <Badge variant="outline">{data.exceso_stock.length}</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {data.exceso_stock.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-10 px-4">
                  No se detectaron excesos de stock en el período analizado.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Producto</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Stock</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Vel. sem.</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Vendido per.</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Comprado per.</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Exceso compra</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Sem. hasta agotar</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Val. inmovilizado</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {data.exceso_stock.map(e => (
                        <tr key={e.producto_id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2 font-medium max-w-[160px] truncate">{e.producto_nombre}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(e.stock_actual)}</td>
                          <td className="px-4 py-2 text-right font-mono text-muted-foreground">{e.velocidad_semanal}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(e.vendido_periodo)}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(e.comprado_periodo)}</td>
                          <td className="px-4 py-2 text-right font-mono text-amber-600 font-bold">{formatNum(e.exceso_vs_venta)}</td>
                          <td className="px-4 py-2 text-right font-mono">{e.semanas_para_agotar} sem.</td>
                          <td className="px-4 py-2 text-right font-mono text-red-600">{formatPYG(e.valor_inmovilizado)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Sin ventas recientes */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                Sin ventas en las últimas {semanas} semanas
                {data.sin_ventas_recientes.length > 0 && <Badge variant="destructive">{data.sin_ventas_recientes.length}</Badge>}
              </CardTitle>
              <CardDescription className="text-xs">Productos con stock disponible pero sin movimiento de venta reciente</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {data.sin_ventas_recientes.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-10 px-4">
                  Todos los productos con stock tienen ventas recientes.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Producto</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Stock actual</th>
                        <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Valor inmovilizado</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {data.sin_ventas_recientes.map(s => (
                        <tr key={s.producto_id} className="hover:bg-muted/30 transition-colors">
                          <td className="px-4 py-2 font-medium">{s.producto_nombre}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(s.stock_actual)}</td>
                          <td className="px-4 py-2 text-right font-mono text-red-600">{formatPYG(s.valor_inmovilizado)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────
const BusinessIntelligence = () => {
  const { empresa, API_URL, token } = useApp();

  return (
    <div className="p-4 md:p-6 space-y-4 max-w-screen-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10 text-primary">
          <BarChart2 className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">Business Intelligence</h1>
          <p className="text-xs text-muted-foreground">Análisis avanzado de patrones para la toma de decisiones</p>
        </div>
      </div>

      <Tabs defaultValue="estadisticas" className="space-y-4">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="estadisticas" className="gap-1.5 text-xs sm:text-sm">
            <TrendingUp className="h-3.5 w-3.5" />
            Estadísticas ventas
          </TabsTrigger>
          <TabsTrigger value="cierre" className="gap-1.5 text-xs sm:text-sm">
            <DollarSign className="h-3.5 w-3.5" />
            Cierre financiero
          </TabsTrigger>
          <TabsTrigger value="sugerencias" className="gap-1.5 text-xs sm:text-sm">
            <Lightbulb className="h-3.5 w-3.5" />
            Sugerencias compra
          </TabsTrigger>
          <TabsTrigger value="exceso" className="gap-1.5 text-xs sm:text-sm">
            <AlertTriangle className="h-3.5 w-3.5" />
            Exceso de stock
          </TabsTrigger>
        </TabsList>

        <TabsContent value="estadisticas">
          <TabEstadisticas empresa={empresa} API_URL={API_URL} token={token} />
        </TabsContent>

        <TabsContent value="cierre">
          <TabCierre empresa={empresa} API_URL={API_URL} token={token} />
        </TabsContent>

        <TabsContent value="sugerencias">
          <TabSugerencias empresa={empresa} API_URL={API_URL} token={token} />
        </TabsContent>

        <TabsContent value="exceso">
          <TabExceso empresa={empresa} API_URL={API_URL} token={token} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default BusinessIntelligence;
