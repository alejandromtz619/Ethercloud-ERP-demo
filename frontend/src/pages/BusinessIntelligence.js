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
  ShoppingBag, Loader2, Target, BoxesIcon, BarChart2, Lightbulb, FileSpreadsheet,
  Search, X, MousePointerClick, Clock, ChevronDown, ChevronRight, CalendarDays,
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
  const [downloading, setDownloading] = useState(false);
  const [periodo, setPeriodo] = useState('semanal');
  const [periodos, setPeriodos] = useState('8');
  const [metrica, setMetrica] = useState('ventas');
  const [productoSearch, setProductoSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState(null); // { id, nombre }
  const [productoEvolucion, setProductoEvolucion] = useState(null);
  const [loadingEvolucion, setLoadingEvolucion] = useState(false);

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

  const downloadExcel = useCallback(async () => {
    if (!empresa) return;
    setDownloading(true);
    try {
      const res = await window.fetch(
        `${API_URL}/bi/estadisticas-productos/excel?empresa_id=${empresa.id}&periodo=${periodo}&periodos=${periodos}&metrica=${metrica}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Error al generar Excel');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bi_productos_${metrica}_${new Date().toISOString().split('T')[0]}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setDownloading(false);
    }
  }, [empresa, API_URL, token, periodo, periodos, metrica]);

  const fetchProductoEvolucion = useCallback(async (pid) => {
    if (!empresa || !pid) return;
    setLoadingEvolucion(true);
    try {
      const res = await window.fetch(
        `${API_URL}/bi/producto-evolucion?empresa_id=${empresa.id}&producto_id=${pid}&periodo=${periodo}&periodos=${periodos}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Error al cargar evolución del producto');
      setProductoEvolucion(await res.json());
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoadingEvolucion(false);
    }
  }, [empresa, API_URL, token, periodo, periodos]);

  useEffect(() => {
    if (selectedProduct) fetchProductoEvolucion(selectedProduct.id);
    else setProductoEvolucion(null);
  }, [selectedProduct, fetchProductoEvolucion]);

  // Reset selected product when period changes so evolution chart re-fetches
  useEffect(() => {
    if (selectedProduct) fetchProductoEvolucion(selectedProduct.id);
  }, [periodo, periodos]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { fetch(); }, [fetch]);

  const TOP_N = 30;
  const topBar = (data?.productos?.slice(0, TOP_N) || []).map(p => ({
    name: p.producto_nombre.length > 22 ? p.producto_nombre.slice(0, 20) + '…' : p.producto_nombre,
    ventas: p.total_ventas,
    unidades: p.total_unidades,
    ganancia: p.ganancia_bruta,
  }));

  const metricaLabel = { ventas: 'Ingresos (₲)', unidades: 'Unidades vendidas', ganancia: 'Ganancia bruta (₲)' }[metrica];
  const periodoLabel = periodo === 'semanal' ? 'semana' : 'mes';
  const promHeaderLabel = periodo === 'semanal' ? 'Promedio/semana' : 'Promedio/mes';
  const curHeaderLabel = periodo === 'semanal' ? 'Esta semana' : 'Este mes';
  const prevHeaderLabel = periodo === 'semanal' ? 'Sem. anterior' : 'Mes anterior';
  const barChartHeight = Math.max(300, topBar.length * 30);
  const filteredProducts = (data?.productos || []).filter(p =>
    p.producto_nombre.toLowerCase().includes(productoSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-1">
              <Label className="text-xs">Período</Label>
              <Select value={periodo} onValueChange={v => { setPeriodo(v); setSelectedProduct(null); }}>
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
              <Label className="text-xs">Métrica</Label>
              <Select value={metrica} onValueChange={setMetrica}>
                <SelectTrigger className="w-36 h-8 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ventas">Ventas (₲)</SelectItem>
                  <SelectItem value="ganancia">Ganancia (₲)</SelectItem>
                  <SelectItem value="unidades">Unidades vendidas</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Buscar producto</Label>
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  value={productoSearch}
                  onChange={e => setProductoSearch(e.target.value)}
                  placeholder="Filtrar tabla…"
                  className="h-8 text-sm pl-7 pr-7 w-44 rounded-md border border-input bg-background px-3 py-1 shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
                {productoSearch && (
                  <button onClick={() => setProductoSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={fetch} disabled={loading} className="h-8 gap-1">
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              Actualizar
            </Button>
            <Button size="sm" variant="outline" onClick={downloadExcel} disabled={downloading || !data} className="h-8 gap-1 text-emerald-700 border-emerald-300 hover:bg-emerald-50">
              {downloading
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <FileSpreadsheet className="h-3.5 w-3.5" />}
              Exportar Excel
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
                        (name === 'ventas' || name === 'ganancia') ? formatPYG(value) : formatNum(value),
                        name === 'ventas' ? 'Ventas' : name === 'ganancia' ? 'Ganancia' : 'Unidades',
                      ]}
                    />
                    <Bar dataKey={metrica} fill="#0044CC" radius={[4, 4, 0, 0]} opacity={0.85} />
                    <Line type="monotone" dataKey={metrica} stroke="#FF6B00" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Top N Bar */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">Top {topBar.length} productos — {metricaLabel}</CardTitle>
              <CardDescription className="text-xs">Ordenados por {metricaLabel.toLowerCase()} en el período seleccionado</CardDescription>
            </CardHeader>
            <CardContent>
              <div style={{ height: barChartHeight }} className="w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topBar} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10 }} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={140} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }}
                      formatter={(v) => [metrica === 'unidades' ? formatNum(v) : formatPYG(v)]}
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
              <div className="flex items-start justify-between gap-2">
                <div>
                  <CardTitle className="text-sm font-semibold">Detalle por producto</CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    {filteredProducts.length} producto{filteredProducts.length !== 1 ? 's' : ''} — comparativa {curHeaderLabel.toLowerCase()} vs. {prevHeaderLabel.toLowerCase()} &middot; Hacé clic en una fila para ver su evolución
                  </CardDescription>
                </div>
                {selectedProduct && (
                  <button
                    onClick={() => setSelectedProduct(null)}
                    className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 shrink-0 mt-0.5"
                  >
                    <X className="h-3 w-3" /> Deseleccionar
                  </button>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">#</th>
                      <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Producto</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Ventas totales (₲)</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Ganancia (₲)</th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground" title={`Total de unidades vendidas en los últimos ${periodos} ${periodoLabel}s`}>Uds. vendidas<br /><span className="font-normal text-[10px] text-muted-foreground/70">{periodos} {periodoLabel}s</span></th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">{curHeaderLabel}<br /><span className="font-normal text-[10px] text-muted-foreground/70">uds. vendidas</span></th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">{prevHeaderLabel}<br /><span className="font-normal text-[10px] text-muted-foreground/70">uds. vendidas</span></th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">{promHeaderLabel}<br /><span className="font-normal text-[10px] text-muted-foreground/70">uds. vendidas</span></th>
                      <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Stock actual</th>
                      <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Variación</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredProducts.length === 0 && (
                      <tr><td colSpan={10} className="px-4 py-8 text-center text-muted-foreground">Sin resultados para "{productoSearch}"</td></tr>
                    )}
                    {filteredProducts.map((p, idx) => {
                      const isSelected = selectedProduct?.id === p.producto_id;
                      return (
                        <tr
                          key={p.producto_id}
                          onClick={() => setSelectedProduct(isSelected ? null : { id: p.producto_id, nombre: p.producto_nombre })}
                          className={cn(
                            'cursor-pointer transition-colors',
                            isSelected ? 'bg-primary/10 border-l-2 border-l-primary' : 'hover:bg-muted/30'
                          )}
                        >
                          <td className="px-4 py-2 text-muted-foreground">{idx + 1}</td>
                          <td className="px-4 py-2 font-medium max-w-[200px]">
                            <div className="flex items-center gap-1.5">
                              {isSelected && <MousePointerClick className="h-3 w-3 text-primary shrink-0" />}
                              <span className="truncate">{p.producto_nombre}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2 text-right font-mono">{formatPYG(p.total_ventas)}</td>
                          <td className="px-4 py-2 text-right font-mono text-emerald-600">{formatPYG(p.ganancia_bruta)}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(p.total_unidades)}</td>
                          <td className="px-4 py-2 text-right font-mono font-semibold">{formatNum(p.periodo_actual_unidades)}</td>
                          <td className="px-4 py-2 text-right font-mono text-muted-foreground">{formatNum(p.periodo_anterior_unidades)}</td>
                          <td className="px-4 py-2 text-right font-mono text-muted-foreground">{p.promedio_por_periodo}</td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(p.stock_actual)}</td>
                          <td className="px-4 py-2 text-center"><VariacionBadge pct={p.variacion_pct} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Per-product evolution chart */}
          {selectedProduct && (
            <Card className="border-primary/30 border">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-semibold">Evolución: {selectedProduct.nombre}</CardTitle>
                    <CardDescription className="text-xs">Últimos {periodos} períodos ({periodo})</CardDescription>
                  </div>
                  <button onClick={() => setSelectedProduct(null)} className="text-muted-foreground hover:text-foreground">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </CardHeader>
              <CardContent>
                {loadingEvolucion ? (
                  <div className="flex items-center justify-center h-48 text-muted-foreground gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" /> Cargando evolución…
                  </div>
                ) : productoEvolucion ? (
                  <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={productoEvolucion.tendencia}>
                        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                        <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={45} />
                        <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
                        <Tooltip
                          contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px' }}
                          formatter={(value, name) => [
                            name === 'Unidades vendidas' ? `${formatNum(value)} uds.` : formatPYG(value),
                            name,
                          ]}
                        />
                        <Legend wrapperStyle={{ fontSize: '11px' }} />
                        <Bar yAxisId="left" dataKey="ventas" name="Ventas (₲)" fill="#0044CC" radius={[4, 4, 0, 0]} opacity={0.85} />
                        <Bar yAxisId="left" dataKey="ganancia" name="Ganancia (₲)" fill="#10b981" radius={[4, 4, 0, 0]} opacity={0.7} />
                        <Line yAxisId="right" type="monotone" dataKey="unidades" name="Unidades vendidas" stroke="#FF6B00" strokeWidth={2} dot={{ r: 3 }} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          )}
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
    { name: 'Gastos operativos', value: data.gastos_operativos?.total || 0 },
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

          {/* Stock valor + Gastos operativos */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {(data.valor_stock_actual?.total || 0) > 0 && (
              <KpiCard
                title="Valor excedente en stock"
                value={formatPYG(data.valor_stock_actual.total)}
                sub={`${formatNum(data.valor_stock_actual.num_tandas)} tandas · ${formatNum(data.valor_stock_actual.num_productos)} productos`}
                icon={BoxesIcon}
                colorClass="text-cyan-500"
              />
            )}
            {(data.gastos_operativos?.total || 0) > 0 && (
              <KpiCard
                title="Gastos operativos"
                value={formatPYG(data.gastos_operativos.total)}
                sub={`${formatNum(data.gastos_operativos.cantidad)} gastos registrados`}
                icon={AlertTriangle}
                colorClass="text-red-600"
              />
            )}
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
                  <p className="text-xs text-muted-foreground mt-0.5">Ganancia bruta − Salarios pagados − Gastos operativos</p>
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
// TAB 5 — Aging de Tandas
// ─────────────────────────────────────────────────────────────────────────────
const TabAging = ({ empresa, API_URL, token }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [orden, setOrden] = useState('mas_antiguo');
  const [expandidos, setExpandidos] = useState({});

  const cargar = useCallback(async () => {
    if (!empresa?.id) return;
    setLoading(true);
    try {
      const r = await fetch(`${API_URL}/bi/aging-tandas?empresa_id=${empresa.id}&orden=${orden}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error('Error al cargar aging de tandas');
      const d = await r.json();
      setData(d);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [empresa, API_URL, token, orden]);

  useEffect(() => { cargar(); }, [cargar]);

  const toggleExpand = (pid) =>
    setExpandidos(prev => ({ ...prev, [pid]: !prev[pid] }));

  const agingBadge = (dias) => {
    if (dias < 30) return 'bg-green-500/10 text-green-600 border border-green-500/20';
    if (dias < 60) return 'bg-yellow-500/10 text-yellow-600 border border-yellow-500/20';
    if (dias < 90) return 'bg-orange-500/10 text-orange-600 border border-orange-500/20';
    return 'bg-red-500/10 text-red-600 border border-red-500/20';
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <Card>
        <CardContent className="pt-4 pb-3">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Ordenar por</Label>
              <Select value={orden} onValueChange={setOrden}>
                <SelectTrigger className="w-52 h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mas_antiguo">Más antiguos primero</SelectItem>
                  <SelectItem value="mas_nuevo">Más nuevos primero</SelectItem>
                  <SelectItem value="mayor_valor">Mayor valor inmovilizado</SelectItem>
                  <SelectItem value="nombre">Nombre A → Z</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button size="sm" variant="outline" onClick={cargar} disabled={loading} className="h-8 text-xs gap-1.5">
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Actualizar
            </Button>
            {data && (
              <p className="text-xs text-muted-foreground ml-auto self-center">
                Calculado al {data.fecha_calculo} · Solo productos activos con stock &gt; 0
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* KPI cards */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <KpiCard
            title="Productos con stock activo"
            value={data.resumen.productos_activos_con_stock}
            icon={Package}
            colorClass="text-blue-500"
          />
          <KpiCard
            title="Tandas activas"
            value={data.resumen.total_tandas_activas}
            icon={Clock}
            colorClass="text-amber-500"
          />
          <KpiCard
            title="Capital inmovilizado"
            value={formatPYG(data.resumen.valor_stock_activo)}
            icon={DollarSign}
            colorClass="text-red-500"
          />
        </div>
      )}

      {/* Color legend */}
      {data && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-muted-foreground font-medium mr-1">Antigüedad:</span>
          <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-600 border border-green-500/20">&lt; 30 días</span>
          <span className="px-2 py-0.5 rounded bg-yellow-500/10 text-yellow-600 border border-yellow-500/20">30 – 59 días</span>
          <span className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-600 border border-orange-500/20">60 – 89 días</span>
          <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-600 border border-red-500/20">≥ 90 días</span>
        </div>
      )}

      {/* Loading spinner */}
      {loading && !data && (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state */}
      {data && data.productos.length === 0 && (
        <Card>
          <CardContent className="flex items-center justify-center h-40 text-muted-foreground text-sm">
            No hay tandas activas con stock restante.
          </CardContent>
        </Card>
      )}

      {/* Main table */}
      {data && data.productos.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-primary" />
              Detalle por producto
            </CardTitle>
            <CardDescription className="text-xs">
              Clic en una fila para ver el desglose de tandas individuales
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="w-8 px-4 py-2.5"></th>
                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Producto</th>
                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Tandas</th>
                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Uds. restantes</th>
                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Aging máx.</th>
                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Val. inmovilizado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.productos.map(p => (
                    <React.Fragment key={p.producto_id}>
                      {/* Product summary row */}
                      <tr
                        className="hover:bg-muted/30 transition-colors cursor-pointer"
                        onClick={() => toggleExpand(p.producto_id)}
                      >
                        <td className="px-4 py-2.5 text-muted-foreground">
                          {expandidos[p.producto_id]
                            ? <ChevronDown className="h-3.5 w-3.5" />
                            : <ChevronRight className="h-3.5 w-3.5" />}
                        </td>
                        <td className="px-4 py-2.5 font-medium">{p.producto_nombre}</td>
                        <td className="px-4 py-2.5 text-center">
                          <span className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                            {p.num_tandas}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono">{formatNum(p.total_unidades_restantes)}</td>
                        <td className="px-4 py-2.5 text-right">
                          <span className={cn('px-2 py-0.5 rounded font-mono font-semibold', agingBadge(p.dias_aging_max))}>
                            {p.dias_aging_max} días
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-red-500 font-semibold">
                          {formatPYG(p.valor_total_inmovilizado)}
                        </td>
                      </tr>

                      {/* Batch detail rows */}
                      {expandidos[p.producto_id] && p.tandas.map(t => (
                        <tr key={t.tanda_id} className="bg-muted/20 border-l-2 border-primary/40">
                          <td className="px-4 py-2"></td>
                          <td className="px-4 py-2 pl-8" colSpan={1}>
                            <div className="flex flex-wrap items-center gap-1.5 text-muted-foreground">
                              <Clock className="h-3 w-3 shrink-0" />
                              <span className="font-medium text-foreground">
                                {t.fecha_entrada
                                  ? new Date(t.fecha_entrada).toLocaleDateString('es-PY')
                                  : '—'}
                              </span>
                              <span className="opacity-40">·</span>
                              <span>{t.proveedor}</span>
                              {t.almacen && (
                                <><span className="opacity-40">·</span><span className="opacity-70">{t.almacen}</span></>
                              )}
                              {t.notas && (
                                <><span className="opacity-40">·</span><span className="italic opacity-60">{t.notas}</span></>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-2 text-center font-mono text-muted-foreground">
                            {t.cantidad_restante}/{t.cantidad_original}
                            <span className="ml-1 opacity-60">({t.porcentaje_consumido}% cons.)</span>
                          </td>
                          <td className="px-4 py-2 text-right font-mono">{formatNum(t.cantidad_restante)}</td>
                          <td className="px-4 py-2 text-right">
                            <span className={cn('px-2 py-0.5 rounded font-mono', agingBadge(t.dias_aging))}>
                              {t.dias_aging} días
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right font-mono">
                            <div className="text-muted-foreground">{formatPYG(t.valor_inmovilizado)}</div>
                            <div className="text-[10px] opacity-60">@ {formatPYG(t.costo_unitario)}/u</div>
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
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
          <TabsTrigger value="aging" className="gap-1.5 text-xs sm:text-sm">
            <Clock className="h-3.5 w-3.5" />
            Aging de tandas
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

        <TabsContent value="aging">
          <TabAging empresa={empresa} API_URL={API_URL} token={token} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default BusinessIntelligence;
