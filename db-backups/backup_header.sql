--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: estadodocumentoelectronico; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estadodocumentoelectronico AS ENUM (
    'PENDIENTE',
    'APROBADO',
    'RECHAZADO'
);

--
-- Name: estadoentrega; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estadoentrega AS ENUM (
    'PENDIENTE',
    'EN_CAMINO',
    'ENTREGADO',
    'CANCELADO'
);

--
-- Name: estadomateria; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estadomateria AS ENUM (
    'DISPONIBLE',
    'VENDIDO'
);

--
-- Name: estadoventa; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.estadoventa AS ENUM (
    'BORRADOR',
    'PENDIENTE',
    'CONFIRMADA',
    'ANULADA'
);

--
-- Name: tipodocumento; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipodocumento AS ENUM (
    'BOLETA',
    'FACTURA'
);

--
-- Name: tipomovimientostock; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipomovimientostock AS ENUM (
    'ENTRADA',
    'SALIDA',
    'AJUSTE',
    'TRASPASO'
);

--
-- Name: tipopago; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipopago AS ENUM (
    'EFECTIVO',
    'TARJETA',
    'TRANSFERENCIA',
    'CHEQUE',
    'CREDITO'
);

--
-- Name: tipovehiculo; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipovehiculo AS ENUM (
    'MOTO',
    'AUTOMOVIL',
    'CAMIONETA'
);

--
-- Name: adelantos_salario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.adelantos_salario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: almacenes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.almacenes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: categorias_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categorias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: ciclos_salario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ciclos_salario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: clientes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clientes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: creditos_clientes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.creditos_clientes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: deudas_proveedores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.deudas_proveedores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: documentos_electronicos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentos_electronicos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: documentos_temporales_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentos_temporales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: empresas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.empresas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: entregas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entregas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: facturas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.facturas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: funcionarios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.funcionarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: marcas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.marcas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: materias_laboratorio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.materias_laboratorio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: movimientos_stock_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.movimientos_stock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: pagos_creditos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pagos_creditos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: permisos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permisos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: preferencias_usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.preferencias_usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: productos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.productos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: proveedor_productos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proveedor_productos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: proveedores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proveedores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: stock_actual_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stock_actual_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: vehiculos_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.vehiculos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: venta_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.venta_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: ventas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ventas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: empresas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.empresas (
    id integer NOT NULL DEFAULT nextval('public.empresas_id_seq'::regclass),
    nombre character varying(255) NOT NULL,
    ruc character varying(50) NOT NULL,
    direccion character varying(500),
    telefono character varying(50),
    email character varying(255),
    estado boolean DEFAULT true,
    creado_en timestamp with time zone DEFAULT now(),
    actualizado_en timestamp with time zone,
    logo_url character varying(500)
);

--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuarios (
    id integer NOT NULL DEFAULT nextval('public.usuarios_id_seq'::regclass),
    empresa_id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    nombre character varying(255) NOT NULL,
    apellido character varying(255),
    telefono character varying(50),
    activo boolean DEFAULT true,
    creado_en timestamp with time zone DEFAULT now(),
    actualizado_en timestamp with time zone
);

--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id integer NOT NULL DEFAULT nextval('public.roles_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion character varying(500)
);

--
-- Name: permisos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permisos (
    id integer NOT NULL DEFAULT nextval('public.permisos_id_seq'::regclass),
    clave character varying(100) NOT NULL,
    descripcion character varying(500)
);

--
-- Name: rol_permisos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_permisos (
    rol_id integer NOT NULL,
    permiso_id integer NOT NULL
);

--
-- Name: usuario_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_roles (
    usuario_id integer NOT NULL,
    rol_id integer NOT NULL
);

--
-- Name: clientes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clientes (
    id integer NOT NULL DEFAULT nextval('public.clientes_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    apellido character varying(255),
    ruc character varying(50),
    cedula character varying(50),
    direccion character varying(500),
    telefono character varying(50),
    email character varying(255),
    acepta_cheque boolean DEFAULT false,
    descuento_porcentaje numeric(5,2) DEFAULT 0,
    limite_credito numeric(15,2) DEFAULT 0,
    estado boolean DEFAULT true,
    creado_en timestamp with time zone DEFAULT now()
);

--
-- Name: creditos_clientes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.creditos_clientes (
    id integer NOT NULL DEFAULT nextval('public.creditos_clientes_id_seq'::regclass),
    cliente_id integer NOT NULL,
    venta_id integer,
    monto_original numeric(15,2) NOT NULL,
    monto_pendiente numeric(15,2) NOT NULL,
    descripcion text,
    fecha_venta date DEFAULT CURRENT_DATE,
    pagado boolean DEFAULT false,
    creado_en timestamp with time zone
);

--
-- Name: pagos_creditos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pagos_creditos (
    id integer NOT NULL DEFAULT nextval('public.pagos_creditos_id_seq'::regclass),
    credito_id integer NOT NULL,
    monto numeric(15,2) NOT NULL,
    fecha_pago timestamp with time zone,
    observacion text
);

--
-- Name: proveedores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proveedores (
    id integer NOT NULL DEFAULT nextval('public.proveedores_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    ruc character varying(50),
    direccion character varying(500),
    telefono character varying(50),
    email character varying(255),
    estado boolean DEFAULT true,
    creado_en timestamp with time zone DEFAULT now()
);

--
-- Name: proveedor_productos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proveedor_productos (
    id integer NOT NULL DEFAULT nextval('public.proveedor_productos_id_seq'::regclass),
    proveedor_id integer NOT NULL,
    producto_id integer NOT NULL,
    costo numeric(15,2) NOT NULL
);

--
-- Name: deudas_proveedores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deudas_proveedores (
    id integer NOT NULL DEFAULT nextval('public.deudas_proveedores_id_seq'::regclass),
    proveedor_id integer NOT NULL,
    monto numeric(15,2) NOT NULL,
    descripcion text,
    fecha_emision date DEFAULT CURRENT_DATE,
    fecha_limite date,
    fecha_pago date,
    pagado boolean DEFAULT false,
    creado_en timestamp with time zone DEFAULT now()
);

--
-- Name: categorias; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categorias (
    id integer NOT NULL DEFAULT nextval('public.categorias_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL
);

--
-- Name: marcas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marcas (
    id integer NOT NULL DEFAULT nextval('public.marcas_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL
);

--
-- Name: productos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productos (
    id integer NOT NULL DEFAULT nextval('public.productos_id_seq'::regclass),
    empresa_id integer NOT NULL,
    categoria_id integer,
    marca_id integer,
    nombre character varying(255) NOT NULL,
    descripcion text,
    codigo_barra character varying(100),
    precio_venta numeric(15,2) NOT NULL,
    fecha_vencimiento date,
    activo boolean DEFAULT true,
    imagen_url character varying(500),
    stock_minimo integer DEFAULT 10
);

--
-- Name: materias_laboratorio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.materias_laboratorio (
    id integer NOT NULL DEFAULT nextval('public.materias_laboratorio_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    descripcion text,
    codigo_barra character varying(100),
    precio numeric(15,2) NOT NULL,
    estado public.estadomateria DEFAULT 'DISPONIBLE'::public.estadomateria,
    creado_en timestamp with time zone
);

--
-- Name: almacenes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.almacenes (
    id integer NOT NULL DEFAULT nextval('public.almacenes_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    ubicacion character varying(500)
);

--
-- Name: stock_actual; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stock_actual (
    id integer NOT NULL DEFAULT nextval('public.stock_actual_id_seq'::regclass),
    producto_id integer NOT NULL,
    almacen_id integer NOT NULL,
    cantidad integer DEFAULT 0,
    alerta_minima integer
);

--
-- Name: movimientos_stock; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimientos_stock (
    id integer NOT NULL DEFAULT nextval('public.movimientos_stock_id_seq'::regclass),
    producto_id integer NOT NULL,
    almacen_id integer NOT NULL,
    tipo public.tipomovimientostock NOT NULL,
    cantidad integer NOT NULL,
    referencia_tipo character varying(50),
    referencia_id integer,
    creado_en timestamp with time zone
);

--
-- Name: ventas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ventas (
    id integer NOT NULL DEFAULT nextval('public.ventas_id_seq'::regclass),
    empresa_id integer NOT NULL,
    cliente_id integer NOT NULL,
    usuario_id integer NOT NULL,
    representante_cliente_id integer,
    total numeric(15,2) DEFAULT 0,
    iva numeric(15,2) DEFAULT 0,
    descuento numeric(15,2) DEFAULT 0,
    tipo_pago public.tipopago DEFAULT 'EFECTIVO'::public.tipopago,
    es_delivery boolean DEFAULT false,
    estado public.estadoventa DEFAULT 'BORRADOR'::public.estadoventa,
    creado_en timestamp with time zone
);

--
-- Name: venta_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.venta_items (
    id integer NOT NULL DEFAULT nextval('public.venta_items_id_seq'::regclass),
    venta_id integer NOT NULL,
    producto_id integer,
    materia_laboratorio_id integer,
    cantidad integer NOT NULL,
    precio_unitario numeric(15,2) NOT NULL,
    total numeric(15,2) NOT NULL,
    observaciones text
);

--
-- Name: funcionarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.funcionarios (
    id integer NOT NULL DEFAULT nextval('public.funcionarios_id_seq'::regclass),
    empresa_id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    apellido character varying(255),
    cedula character varying(50),
    cargo character varying(255),
    salario_base numeric(15,2) DEFAULT 0,
    ips numeric(15,2),
    fecha_nacimiento date,
    activo boolean DEFAULT true
);

--
-- Name: adelantos_salario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.adelantos_salario (
    id integer NOT NULL DEFAULT nextval('public.adelantos_salario_id_seq'::regclass),
    funcionario_id integer NOT NULL,
    monto numeric(15,2) NOT NULL,
    creado_en timestamp with time zone DEFAULT now()
);

--
-- Name: ciclos_salario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ciclos_salario (
    id integer NOT NULL DEFAULT nextval('public.ciclos_salario_id_seq'::regclass),
    funcionario_id integer NOT NULL,
    periodo character varying(7),
    fecha_inicio date,
    fecha_fin date,
    salario_base numeric(15,2) DEFAULT 0,
    descuentos numeric(15,2) DEFAULT 0,
    salario_neto numeric(15,2) DEFAULT 0,
    pagado boolean DEFAULT false,
    fecha_pago timestamp with time zone
);

--
-- Name: vehiculos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vehiculos (
    id integer NOT NULL DEFAULT nextval('public.vehiculos_id_seq'::regclass),
    empresa_id integer NOT NULL,
    tipo public.tipovehiculo NOT NULL,
    chapa character varying(20) NOT NULL,
    vencimiento_habilitacion date,
    vencimiento_cedula_verde date
);

--
-- Name: entregas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entregas (
    id integer NOT NULL DEFAULT nextval('public.entregas_id_seq'::regclass),
    venta_id integer NOT NULL,
    vehiculo_id integer,
    responsable_usuario_id integer,
    fecha_entrega timestamp with time zone,
    estado public.estadoentrega DEFAULT 'PENDIENTE'::public.estadoentrega
);

--
-- Name: facturas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facturas (
    id integer NOT NULL DEFAULT nextval('public.facturas_id_seq'::regclass),
    venta_id integer NOT NULL,
    numero character varying(50) NOT NULL,
    total numeric(15,2) NOT NULL,
    iva numeric(15,2) NOT NULL,
    estado character varying(50) DEFAULT 'EMITIDA',
    creado_en timestamp with time zone
);

--
-- Name: documentos_electronicos; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentos_electronicos (
    id integer NOT NULL DEFAULT nextval('public.documentos_electronicos_id_seq'::regclass),
    factura_id integer NOT NULL,
    ruta_xml character varying(500),
    cdc character varying(100),
    estado_sifen public.estadodocumentoelectronico DEFAULT 'PENDIENTE'::public.estadodocumentoelectronico,
    mensaje_respuesta text,
    creado_en timestamp with time zone DEFAULT now()
);

--
-- Name: documentos_temporales; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentos_temporales (
    id integer NOT NULL DEFAULT nextval('public.documentos_temporales_id_seq'::regclass),
    token character varying(255) NOT NULL,
    venta_id integer NOT NULL,
    tipo_documento public.tipodocumento NOT NULL,
    file_path character varying(500) NOT NULL,
    fecha_creacion timestamp with time zone,
    fecha_expiracion timestamp with time zone NOT NULL,
    descargas integer DEFAULT 0,
    empresa_id integer NOT NULL
);

--
-- Name: preferencias_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.preferencias_usuario (
    id integer NOT NULL DEFAULT nextval('public.preferencias_usuario_id_seq'::regclass),
    usuario_id integer NOT NULL,
    tema character varying(50) DEFAULT 'light',
    color_primario character varying(50) DEFAULT '#0044CC'
);

--
-- Name: adelantos_salario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adelantos_salario ALTER COLUMN id SET DEFAULT nextval('public.adelantos_salario_id_seq'::regclass);


--
-- Name: almacenes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.almacenes ALTER COLUMN id SET DEFAULT nextval('public.almacenes_id_seq'::regclass);


--
-- Name: categorias id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categorias ALTER COLUMN id SET DEFAULT nextval('public.categorias_id_seq'::regclass);


--
-- Name: ciclos_salario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ciclos_salario ALTER COLUMN id SET DEFAULT nextval('public.ciclos_salario_id_seq'::regclass);


--
-- Name: clientes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes ALTER COLUMN id SET DEFAULT nextval('public.clientes_id_seq'::regclass);


--
-- Name: creditos_clientes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creditos_clientes ALTER COLUMN id SET DEFAULT nextval('public.creditos_clientes_id_seq'::regclass);


--
-- Name: deudas_proveedores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deudas_proveedores ALTER COLUMN id SET DEFAULT nextval('public.deudas_proveedores_id_seq'::regclass);


--
-- Name: documentos_electronicos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_electronicos ALTER COLUMN id SET DEFAULT nextval('public.documentos_electronicos_id_seq'::regclass);


--
-- Name: documentos_temporales id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_temporales ALTER COLUMN id SET DEFAULT nextval('public.documentos_temporales_id_seq'::regclass);


--
-- Name: empresas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.empresas ALTER COLUMN id SET DEFAULT nextval('public.empresas_id_seq'::regclass);


--
-- Name: entregas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entregas ALTER COLUMN id SET DEFAULT nextval('public.entregas_id_seq'::regclass);


--
-- Name: facturas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facturas ALTER COLUMN id SET DEFAULT nextval('public.facturas_id_seq'::regclass);


--
-- Name: funcionarios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.funcionarios ALTER COLUMN id SET DEFAULT nextval('public.funcionarios_id_seq'::regclass);


--
-- Name: marcas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marcas ALTER COLUMN id SET DEFAULT nextval('public.marcas_id_seq'::regclass);


--
-- Name: materias_laboratorio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materias_laboratorio ALTER COLUMN id SET DEFAULT nextval('public.materias_laboratorio_id_seq'::regclass);


--
-- Name: movimientos_stock id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_stock ALTER COLUMN id SET DEFAULT nextval('public.movimientos_stock_id_seq'::regclass);


--
-- Name: pagos_creditos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_creditos ALTER COLUMN id SET DEFAULT nextval('public.pagos_creditos_id_seq'::regclass);


--
-- Name: permisos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permisos ALTER COLUMN id SET DEFAULT nextval('public.permisos_id_seq'::regclass);


--
-- Name: preferencias_usuario id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencias_usuario ALTER COLUMN id SET DEFAULT nextval('public.preferencias_usuario_id_seq'::regclass);


--
-- Name: productos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos ALTER COLUMN id SET DEFAULT nextval('public.productos_id_seq'::regclass);


--
-- Name: proveedor_productos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor_productos ALTER COLUMN id SET DEFAULT nextval('public.proveedor_productos_id_seq'::regclass);


--
-- Name: proveedores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores ALTER COLUMN id SET DEFAULT nextval('public.proveedores_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: stock_actual id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_actual ALTER COLUMN id SET DEFAULT nextval('public.stock_actual_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


--
-- Name: vehiculos id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehiculos ALTER COLUMN id SET DEFAULT nextval('public.vehiculos_id_seq'::regclass);


--
-- Name: venta_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_items ALTER COLUMN id SET DEFAULT nextval('public.venta_items_id_seq'::regclass);


--
-- Name: ventas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas ALTER COLUMN id SET DEFAULT nextval('public.ventas_id_seq'::regclass);


