LY public.venta_items ALTER COLUMN id SET DEFAULT nextval('public.venta_items_id_seq'::regclass);


--
-- Name: ventas id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas ALTER COLUMN id SET DEFAULT nextval('public.ventas_id_seq'::regclass);


--
-- Data for Name: adelantos_salario; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.adelantos_salario (id, funcionario_id, monto, creado_en) FROM stdin;
1	1	300000.00	2026-02-22 16:26:49.053456+00
\.


--
-- Data for Name: almacenes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.almacenes (id, empresa_id, nombre, ubicacion) FROM stdin;
1	1	Deposito	Matriz
2	1	Tienda	Matriz
\.


--
-- Data for Name: categorias; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.categorias (id, empresa_id, nombre) FROM stdin;
\.


--
-- Data for Name: ciclos_salario; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ciclos_salario (id, funcionario_id, periodo, fecha_inicio, fecha_fin, salario_base, descuentos, salario_neto, pagado, fecha_pago) FROM stdin;
\.


--
-- Data for Name: clientes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.clientes (id, empresa_id, nombre, apellido, ruc, cedula, direccion, telefono, email, acepta_cheque, descuento_porcentaje, limite_credito, estado, creado_en) FROM stdin;
2	1	Cliente	Prueba Segundo	87968451	6874153	Av. Siempre Muerta	0996549871	hola@example.com	f	0.00	1.00	t	2026-02-03 14:06:31.922543+00
1	1	Cliente	Prueba	12310-0	31561	Av. Siempre viva	0987456123	asldkmas@aslkdm	t	20.00	500000.00	t	2026-02-03 14:05:22.266466+00
3	1	Alejandro	Martinez	5244360-4	5244360	Km8 Acaray	0976574271	alejandro.zenitram619@gmail.com	t	10.00	300000.00	t	2026-02-09 17:45:49.02321+00
4	1	Angel	Torales	5868388-1	5868388	Km4 Avenida Principal	0975441953		f	0.00	0.00	t	2026-02-09 19:26:55.751881+00
\.


--
-- Data for Name: creditos_clientes; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.creditos_clientes (id, cliente_id, venta_id, monto_original, monto_pendiente, descripcion, fecha_venta, pagado, creado_en) FROM stdin;
1	1	2	72250.00	0.00	Venta #2	2026-02-03	t	2026-02-03 16:43:20.764477+00
4	1	5	76500.00	0.00	Venta #5	2026-02-04	t	2026-02-04 00:43:41.876141+00
6	1	15	289000.00	0.00	Venta #15	2026-02-04	t	2026-02-04 17:47:00.691027+00
5	1	12	123250.00	0.00	Venta #12	2026-02-04	t	2026-02-04 17:30:42.675627+00
8	1	19	72250.00	0.00	Venta #19	2026-02-04	t	2026-02-04 18:35:27.481865+00
7	1	16	51000.00	0.00	Venta #16	2026-02-04	t	2026-02-04 18:05:43.212265+00
14	1	30	51000.00	51000.00	Venta #30	2026-02-05	f	2026-02-05 20:40:04.682284+00
13	1	27	72250.00	0.00	Venta #27	2026-02-04	t	2026-02-04 20:26:19.57393+00
\.


--
-- Data for Name: deudas_proveedores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.deudas_proveedores (id, proveedor_id, monto, descripcion, fecha_emision, fecha_limite, fecha_pago, pagado, creado_en) FROM stdin;
1	1	500000.00	Mensualidad Software	2026-02-03	2026-02-28	2026-02-04	t	2026-02-03 14:49:16.826851+00
2	2	600000.00	mercaderia	2026-02-05	2026-02-28	2026-02-06	t	2026-02-05 20:05:24.578608+00
\.


--
-- Data for Name: documentos_electronicos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documentos_electronicos (id, factura_id, ruta_xml, cdc, estado_sifen, mensaje_respuesta, creado_en) FROM stdin;
\.


--
-- Data for Name: documentos_temporales; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.documentos_temporales (id, token, venta_id, tipo_documento, file_path, fecha_creacion, fecha_expiracion, descargas, empresa_id) FROM stdin;
1	fa59e6c3-a890-4306-b510-3d5c51e46a62	49	BOLETA	/tmp/documentos/boleta_49_fa59e6c3-a890-4306-b510-3d5c51e46a62.pdf	2026-02-09 19:23:21.784829+00	2026-03-11 19:23:21.784764+00	4	1
2	b202ca82-60d3-45a4-8679-854854c3abe9	50	BOLETA	/tmp/documentos/boleta_50_b202ca82-60d3-45a4-8679-854854c3abe9.pdf	2026-02-09 19:27:35.708523+00	2026-03-11 19:27:35.708463+00	5	1
3	f15707bf-5843-4ee0-ac7a-93ea72c84d2c	51	BOLETA	/tmp/documentos/boleta_51_f15707bf-5843-4ee0-ac7a-93ea72c84d2c.pdf	2026-02-09 21:11:20.973406+00	2026-03-11 21:11:20.973354+00	2	1
4	7f94de72-6bcb-407b-b880-c7e29b5d7166	52	BOLETA	/tmp/documentos/boleta_52_7f94de72-6bcb-407b-b880-c7e29b5d7166.pdf	2026-02-10 18:08:05.599756+00	2026-03-12 18:08:05.599719+00	4	1
5	c178e148-fb76-40d1-8bea-67952e194240	54	BOLETA	/tmp/documentos/boleta_54_c178e148-fb76-40d1-8bea-67952e194240.pdf	2026-02-10 19:00:33.022375+00	2026-03-12 19:00:33.022201+00	3	1
6	e4fec64b-9b96-4842-9803-0d90289858b4	55	BOLETA	/tmp/documentos/boleta_55_e4fec64b-9b96-4842-9803-0d90289858b4.pdf	2026-02-10 19:05:22.086649+00	2026-03-12 19:05:22.086533+00	2	1
7	457a5151-f4c8-44f0-8c4a-09038ead5f72	61	BOLETA	/app/uploads/documentos/boleta_61_457a5151-f4c8-44f0-8c4a-09038ead5f72.pdf	2026-02-15 23:29:02.33152+00	2026-03-17 23:29:02.331455+00	4	1
\.


--
-- Data for Name: empresas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.empresas (id, nombre, ruc, direccion, telefono, email, estado, creado_en, actualizado_en, logo_url) FROM stdin;
1	Luz Brill S.A.	12345678901	Av. Principal 123	123456789	contacto@luzbrill.com	t	2026-02-02 21:51:52.584927+00	\N	\N
\.


--
-- Data for Name: entregas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.entregas (id, venta_id, vehiculo_id, responsable_usuario_id, fecha_entrega, estado) FROM stdin;
1	1	1	1	2026-02-03 14:55:26.268+00	ENTREGADO
14	14	2	1	\N	ENTREGADO
19	20	1	1	\N	ENTREGADO
24	25	1	1	\N	ENTREGADO
26	27	1	2	\N	ENTREGADO
32	36	2	1	\N	ENTREGADO
29	30	1	2	\N	ENTREGADO
33	41	1	2	\N	ENTREGADO
35	43	1	2	\N	ENTREGADO
37	45	2	2	\N	ENTREGADO
39	57	1	1	\N	ENTREGADO
40	60	\N	\N	\N	PENDIENTE
\.


--
-- Data for Name: facturas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.facturas (id, venta_id, numero, total, iva, estado, creado_en) FROM stdin;
\.


--
-- Data for Name: funcionarios; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.funcionarios (id, empresa_id, nombre, apellido, cedula, cargo, salario_base, ips, fecha_nacimiento, activo) FROM stdin;
1	1	Empleado	Prueba Primero	123456	Vendedor	3500000.00	320000.00	2002-02-05	t
2	1	Empleado	Prueba Segundo	654321	Delivery	2900000.00	\N	\N	t
\.


--
-- Data for Name: marcas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.marcas (id, empresa_id, nombre) FROM stdin;
1	1	Blascor
2	1	Alba
3	1	Shine
4	1	Prueba
\.


--
-- Data for Name: materias_laboratorio; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.materias_laboratorio (id, empresa_id, nombre, descripcion, codigo_barra, precio, estado, creado_en) FROM stdin;
2	1	Pintura seca	Picanto361	sdf8f23	90000.00	VENDIDO	2026-02-03 14:54:53.777993+00
1	1	Pintura mezcla	Camaro589	asfsg8798	500000.00	VENDIDO	2026-02-03 14:54:32.190837+00
3	1	pintura mojada	land rover 233	fsdfd899	430000.00	VENDIDO	2026-02-04 20:22:08.417271+00
4	1	prueba	lab1	9843894	40000.00	VENDIDO	2026-02-06 20:42:59.5726+00
5	1	Prueba cod	camaro123	LAB7F8FEBF4	50000.00	DISPONIBLE	2026-02-16 18:19:38.337527+00
6	1	prueba 2 cod	picantito234	LAB242E135E	75000.00	DISPONIBLE	2026-02-16 18:47:36.545959+00
\.


--
-- Data for Name: movimientos_stock; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.movimientos_stock (id, producto_id, almacen_id, tipo, cantidad, referencia_tipo, referencia_id, creado_en) FROM stdin;
1	1	1	ENTRADA	50	\N	\N	2026-02-03 14:51:16.209503+00
2	3	2	ENTRADA	80	\N	\N	2026-02-03 14:54:01.582833+00
3	3	2	SALIDA	-3	venta	1	2026-02-03 14:55:36.087317+00
4	3	2	SALIDA	-1	venta	2	2026-02-03 16:43:20.764477+00
5	3	2	SALIDA	-2	venta	11	2026-02-04 17:30:14.170742+00
6	1	1	SALIDA	-2	venta	11	2026-02-04 17:30:14.170742+00
7	1	1	SALIDA	-1	venta	12	2026-02-04 17:30:42.675627+00
8	3	2	SALIDA	-1	venta	12	2026-02-04 17:30:42.675627+00
9	1	1	SALIDA	-1	venta	13	2026-02-04 17:31:26.939694+00
10	1	1	SALIDA	-1	venta	14	2026-02-04 17:42:20.723133+00
11	3	2	SALIDA	-4	venta	15	2026-02-04 17:47:00.691027+00
12	1	1	SALIDA	-1	venta	16	2026-02-04 18:05:43.212265+00
13	1	1	SALIDA	-1	venta	17	2026-02-04 18:23:25.300612+00
14	1	1	SALIDA	-1	venta	18	2026-02-04 18:35:05.48025+00
15	3	2	SALIDA	-1	venta	19	2026-02-04 18:35:27.481865+00
16	1	1	SALIDA	-2	venta	20	2026-02-04 18:56:38.893521+00
17	3	2	SALIDA	-3	venta	21	2026-02-04 19:09:42.164703+00
18	3	1	ENTRADA	3	ANULACION_VENTA	21	2026-02-04 19:10:01.975451+00
19	1	1	SALIDA	-3	venta	22	2026-02-04 19:11:33.398733+00
20	1	1	ENTRADA	3	ANULACION_VENTA	22	2026-02-04 19:13:09.978892+00
21	3	2	SALIDA	-1	venta	23	2026-02-04 19:43:16.714495+00
22	3	2	ENTRADA	1	ANULACION_VENTA	23	2026-02-04 19:44:35.797316+00
23	1	1	SALIDA	-2	venta	24	2026-02-04 19:50:56.301305+00
24	3	2	SALIDA	-1	venta	24	2026-02-04 19:50:56.301305+00
25	1	1	ENTRADA	2	ANULACION_VENTA	24	2026-02-04 19:51:28.860962+00
26	3	2	ENTRADA	1	ANULACION_VENTA	24	2026-02-04 19:51:28.860962+00
27	3	2	SALIDA	-1	venta	25	2026-02-04 20:12:48.626851+00
28	3	2	SALIDA	-1	venta	27	2026-02-04 20:26:19.57393+00
29	1	1	SALIDA	-1	venta	28	2026-02-04 21:18:06.498427+00
30	1	1	ENTRADA	1	ANULACION_VENTA	28	2026-02-04 21:19:14.557707+00
31	1	1	SALIDA	-1	venta	30	2026-02-05 20:40:04.682284+00
32	1	1	SALIDA	-2	venta	31	2026-02-05 20:54:43.671646+00
33	3	2	SALIDA	-3	venta	31	2026-02-05 20:54:43.671646+00
34	1	1	ENTRADA	2	ANULACION_VENTA	31	2026-02-05 20:55:01.246541+00
35	3	2	ENTRADA	3	ANULACION_VENTA	31	2026-02-05 20:55:01.246541+00
36	1	1	SALIDA	-1	venta	32	2026-02-05 21:47:12.794845+00
37	1	1	SALIDA	-1	venta	33	2026-02-05 22:02:30.111324+00
38	1	1	SALIDA	-1	venta	34	2026-02-05 22:02:59.485291+00
39	3	2	SALIDA	-1	venta	36	2026-02-05 22:04:52.837079+00
40	1	1	SALIDA	-2	venta	36	2026-02-05 22:04:52.842+00
41	1	1	SALIDA	-1	venta	37	2026-02-05 22:17:20.841773+00
42	3	2	SALIDA	-1	venta	37	2026-02-05 22:17:20.868651+00
43	1	1	SALIDA	-1	venta	38	2026-02-05 23:11:19.64514+00
44	1	1	ENTRADA	1	ANULACION_VENTA	38	2026-02-05 23:11:38.639399+00
45	1	1	SALIDA	-1	venta	39	2026-02-06 19:13:47.94051+00
46	4	1	ENTRADA	30	\N	\N	2026-02-06 19:19:42.884207+00
47	4	1	ENTRADA	1	\N	\N	2026-02-06 19:38:26.720663+00
48	4	1	SALIDA	-31	\N	\N	2026-02-06 20:02:28.018064+00
49	1	1	SALIDA	-2	venta	40	2026-02-06 20:41:48.957512+00
50	3	2	SALIDA	-1	venta	41	2026-02-06 20:42:32.853191+00
51	5	1	ENTRADA	3	\N	\N	2026-02-06 20:43:25.252139+00
52	5	1	SALIDA	-3	\N	\N	2026-02-06 20:43:31.83753+00
53	1	1	SALIDA	-1	venta	42	2026-02-06 21:19:22.609977+00
54	1	1	SALIDA	-1	venta	43	2026-02-06 21:30:41.694595+00
55	3	2	SALIDA	-2	venta	43	2026-02-06 21:30:41.716168+00
56	3	2	SALIDA	-1	venta	44	2026-02-07 14:01:23.626369+00
57	1	1	SALIDA	-1	venta	44	2026-02-07 14:01:23.631262+00
58	3	2	SALIDA	-1	venta	45	2026-02-09 17:57:56.241806+00
59	3	2	SALIDA	-1	venta	46	2026-02-09 18:28:07.499209+00
60	1	1	SALIDA	-2	venta	46	2026-02-09 18:28:07.525032+00
61	3	2	SALIDA	-1	venta	47	2026-02-09 18:36:13.819556+00
62	1	1	SALIDA	-1	venta	48	2026-02-09 18:44:24.160029+00
63	1	1	SALIDA	-2	venta	49	2026-02-09 18:53:48.70494+00
64	3	2	SALIDA	-1	venta	51	2026-02-09 21:11:10.00641+00
65	3	2	SALIDA	-1	venta	52	2026-02-10 18:07:58.9882+00
66	3	2	SALIDA	-2	venta	53	2026-02-10 18:52:36.345106+00
67	3	2	SALIDA	-4	venta	54	2026-02-10 19:00:27.273476+00
68	3	2	SALIDA	-1	venta	55	2026-02-10 19:05:18.023645+00
69	1	1	SALIDA	-1	venta	55	2026-02-10 19:05:18.04873+00
70	6	1	ENTRADA	100	\N	\N	2026-02-10 19:24:18.148723+00
71	11	1	ENTRADA	100	\N	\N	2026-02-10 19:24:36.573321+00
72	12	1	ENTRADA	100	\N	\N	2026-02-10 19:24:46.938113+00
73	13	1	ENTRADA	100	\N	\N	2026-02-10 19:25:00.621364+00
74	14	1	ENTRADA	100	\N	\N	2026-02-10 19:25:16.534606+00
75	15	1	ENTRADA	100	\N	\N	2026-02-10 19:25:25.354478+00
76	15	1	ENTRADA	100	\N	\N	2026-02-10 19:25:33.653502+00
77	15	1	SALIDA	-100	\N	\N	2026-02-10 19:25:45.229519+00
78	16	1	ENTRADA	100	\N	\N	2026-02-10 19:25:54.081577+00
79	17	1	ENTRADA	100	\N	\N	2026-02-10 19:26:01.492042+00
80	3	2	SALIDA	-1	venta	56	2026-02-10 19:26:27.742765+00
81	1	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.759352+00
82	11	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.76188+00
83	6	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.764102+00
84	12	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.766543+00
85	13	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.768893+00
86	14	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.771061+00
87	15	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.77274+00
88	16	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.774487+00
89	17	1	SALIDA	-1	venta	56	2026-02-10 19:26:27.77612+00
90	18	1	ENTRADA	100	\N	\N	2026-02-10 19:29:15.706976+00
91	3	2	ENTRADA	1	ANULACION_VENTA	52	2026-02-10 20:31:38.343287+00
92	11	1	SALIDA	-1	venta	57	2026-02-10 20:36:50.23037+00
93	6	1	SALIDA	-1	venta	57	2026-02-10 20:36:50.251822+00
94	12	1	SALIDA	-1	venta	57	2026-02-10 20:36:50.254402+00
95	14	1	SALIDA	-1	venta	58	2026-02-10 20:37:18.021894+00
96	15	1	SALIDA	-1	venta	58	2026-02-10 20:37:18.041903+00
97	11	1	ENTRADA	1	\N	\N	2026-02-10 20:39:08.739149+00
98	11	1	SALIDA	-1	venta	59	2026-02-10 20:49:44.433466+00
99	6	1	SALIDA	-1	venta	59	2026-02-10 20:49:44.438283+00
100	6	1	SALIDA	-1	venta	60	2026-02-10 20:54:13.296007+00
101	12	1	SALIDA	-1	venta	60	2026-02-10 20:54:13.300067+00
102	11	1	SALIDA	-1	venta	61	2026-02-15 23:28:54.50961+00
103	6	1	SALIDA	-1	venta	61	2026-02-15 23:28:54.529108+00
104	12	1	SALIDA	-1	venta	61	2026-02-15 23:28:54.532931+00
105	13	1	SALIDA	-1	venta	61	2026-02-15 23:28:54.536112+00
106	11	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.372826+00
107	6	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.392972+00
108	12	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.395423+00
109	13	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.397586+00
110	17	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.399521+00
111	16	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.401405+00
112	15	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.403238+00
113	14	1	SALIDA	-1	venta	62	2026-02-16 00:49:24.405418+00
114	11	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.623509+00
115	6	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.643947+00
116	12	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.646865+00
117	13	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.649706+00
118	14	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.652164+00
119	15	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.654705+00
120	16	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.656911+00
121	17	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.659069+00
122	18	1	SALIDA	-1	venta	63	2026-02-16 00:57:37.661147+00
123	3	2	SALIDA	-1	venta	63	2026-02-16 00:57:37.664815+00
\.


--
-- Data for Name: pagos_creditos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.pagos_creditos (id, credito_id, monto, fecha_pago, observacion) FROM stdin;
1	1	72250.00	2026-02-04 16:54:04.550692+00	maomeno
2	4	76500.00	2026-02-04 18:04:44.171828+00	
3	6	289000.00	2026-02-04 18:04:46.390824+00	
4	5	123250.00	2026-02-04 18:04:48.208851+00	
5	8	72250.00	2026-02-04 19:42:26.832437+00	
6	7	51000.00	2026-02-04 19:42:29.563872+00	
7	13	50000.00	2026-02-05 20:44:49.552744+00	pago parcial
8	13	22250.00	2026-02-05 20:45:08.480407+00	pago total
\.


--
-- Data for Name: permisos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.permisos (id, clave, descripcion) FROM stdin;
33	ventas.crear	Crear ventas
34	ventas.ver	Ver ventas
35	ventas.anular	Anular ventas
36	ventas.modificar_precio	Modificar precios en ventas
37	ventas.aplicar_descuento	Aplicar descuentos
38	ventas.imprimir_boleta	Imprimir boletas
39	ventas.imprimir_factura	Imprimir facturas
40	ventas.ver_historial	Ver historial de ventas
41	productos.ver	Ver productos
42	productos.crear	Crear productos
43	productos.editar	Editar productos
44	productos.eliminar	Eliminar productos
45	productos.modificar_precio	Modificar precios de productos
46	stock.ver	Ver stock
47	stock.entrada	Registrar entrada de stock
48	stock.salida	Registrar salida de stock
49	stock.traspasar	Traspasar stock entre almacenes
50	stock.ajustar	Ajustar stock manualmente
51	clientes.ver	Ver clientes
52	clientes.crear	Crear clientes
53	clientes.editar	Editar clientes
54	clientes.ver_creditos	Ver créditos de clientes
55	proveedores.ver	Ver proveedores
56	proveedores.crear	Crear proveedores
57	proveedores.editar	Editar proveedores
58	proveedores.gestionar_deudas	Gestionar deudas con proveedores
59	funcionarios.ver	Ver funcionarios
60	funcionarios.crear	Crear funcionarios
61	funcionarios.editar	Editar funcionarios
62	funcionarios.ver_salarios	Ver salarios
63	funcionarios.adelantos	Registrar adelantos de salario
64	funcionarios.pagar_salarios	Marcar salarios como pagados
65	delivery.ver	Ver entregas
66	delivery.crear	Crear entregas
67	delivery.actualizar_estado	Actualizar estado de entregas
68	flota.ver	Ver flota
69	flota.gestionar	Gestionar vehículos
70	laboratorio.crear	Crear materias de laboratorio
71	laboratorio.ver	Ver materias de laboratorio
72	usuarios.ver	Ver usuarios
73	usuarios.gestionar	Gestionar usuarios
74	roles.gestionar	Gestionar roles y permisos
75	sistema.configurar	Configurar sistema
76	reportes.ver	Ver reportes
77	reportes.exportar	Exportar reportes
78	facturas.ver	Ver facturas
79	delivery.eliminar	Eliminar entregas
81	dashboard.ver	Ver dashboard
\.


--
-- Data for Name: preferencias_usuario; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.preferencias_usuario (id, usuario_id, tema, color_primario) FROM stdin;
1	1	dark	#000000
2	3	dark	#F97316
\.


--
-- Data for Name: productos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.productos (id, empresa_id, categoria_id, marca_id, nombre, descripcion, codigo_barra, precio_venta, fecha_vencimiento, activo, imagen_url, stock_minimo) FROM stdin;
2	1	\N	1	Blascor Decorativo	1L	1684dsfsf	85000.00	2026-02-28	f	https://www.blascor.com/wp-content/uploads/2022/04/mc-ultra-piso-transparente.png	10
4	1	\N	1	Crema dental	Prueba	7841056006225	5000.00	\N	f	https://flashimportados.s3.sa-east-1.amazonaws.com/products/6a3810ce-bb3b-481f-8435-5de0ad690c0c.webp	10
5	1	\N	\N	prueba	1	089348989	60000.00	\N	f		10
11	1	\N	\N	prueba2		235235	2000.00	\N	t		10
6	1	\N	\N	prueba1		34635234	1000.00	\N	t		10
12	1	\N	\N	prueba3		3468786	2300.00	\N	t		10
13	1	\N	\N	prueba4		sdfgdf545	1250.00	\N	t		10
14	1	\N	\N	prueba5		45746745	3500.00	\N	t		10
15	1	\N	\N	prueba6		346356345	1670.00	\N	t		10
16	1	\N	\N	prueba7		3453523	4000.00	\N	t		10
17	1	\N	\N	prueba8		e464564	8000.00	\N	t		10
18	1	\N	\N	prueba		3453453	4030.00	\N	t		10
3	1	\N	1	Blascor Decorativo	1L	4869dsfs	85000.00	\N	t	https://www.blascor.com/wp-content/uploads/2023/09/texturas-decorativa-balde-16l-1.png	10
1	1	\N	2	Blascor Rojo	1L	8694798dfdvs	60500.00	\N	t	https://www.blascor.com/wp-content/uploads/2022/04/mc-ultra-piso-transparente.png	10
\.


--
-- Data for Name: proveedor_productos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proveedor_productos (id, proveedor_id, producto_id, costo) FROM stdin;
\.


--
-- Data for Name: proveedores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.proveedores (id, empresa_id, nombre, ruc, direccion, telefono, email, estado, creado_en) FROM stdin;
1	1	Ether	5244360-4	Km8 Acaray	0976574271	ether.solucionestech@gmail.com	t	2026-02-03 14:48:47.826235+00
2	1	Proveedor Prueba	43343523	Km10	38923459		t	2026-02-05 20:04:55.061418+00
\.


--
-- Data for Name: rol_permisos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.rol_permisos (rol_id, permiso_id) FROM stdin;
1	33
1	34
1	35
1	36
1	37
1	38
1	39
1	40
1	41
1	42
1	43
1	44
1	45
1	46
1	47
1	48
1	49
1	50
1	51
1	52
1	53
1	54
1	55
1	56
1	57
1	58
1	59
1	60
1	61
1	62
1	63
1	64
1	65
1	66
1	67
1	68
1	69
1	70
1	71
1	72
1	73
1	74
1	75
1	76
1	77
1	78
2	65
2	66
2	67
1	79
1	81
3	33
3	34
3	38
3	39
3	40
3	41
3	42
3	43
3	45
3	46
3	47
3	48
3	49
3	50
3	51
3	52
3	53
3	54
3	65
3	66
3	67
3	68
3	70
3	71
3	81
4	33
4	34
4	37
4	38
4	41
4	46
4	51
3	36
3	37
3	55
3	56
3	57
3	58
3	61
3	59
3	63
3	64
3	62
3	79
3	72
3	76
3	77
3	78
4	65
4	66
4	67
4	68
4	79
4	81
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.roles (id, empresa_id, nombre, descripcion) FROM stdin;
1	1	Administrador	Acceso total al sistema
2	1	Delivery	Entregador de pedidos
3	1	Gerente	Gerente de tienda
4	1	Vendedor	Vendedor de tienda
\.


--
-- Data for Name: stock_actual; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stock_actual (id, producto_id, almacen_id, cantidad, alerta_minima) FROM stdin;
3	3	1	3	\N
1	1	1	20	29
4	4	1	0	\N
5	5	1	0	\N
7	11	1	95	\N
6	6	1	93	\N
8	12	1	94	\N
9	13	1	96	\N
10	14	1	96	\N
11	15	1	96	\N
12	16	1	97	\N
13	17	1	97	\N
14	18	1	99	\N
2	3	2	44	\N
\.


--
-- Data for Name: usuario_roles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.usuario_roles (usuario_id, rol_id) FROM stdin;
1	1
2	2
3	3
4	4
5	3
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.usuarios (id, empresa_id, email, password_hash, nombre, apellido, telefono, activo, creado_en, actualizado_en) FROM stdin;
1	1	admin@luzbrill.com	$2b$12$u8Mk.AmfXJpWj0ZHYUGWgutvjMGKVWuUKH.P1mqPANVg1lxebuW8O	Admin	Sistema	123456789	t	2026-02-02 21:54:35.052016+00	\N
2	1	prueba@delivery	$2b$12$am9dPlC8w/wQplfmSJf3WuxDfCd5pVinmXJeayZIeN61Irc5hcv4y	Prueba	Delivery		t	2026-02-03 22:38:53.568553+00	\N
3	1	prueba@gerente	$2b$12$TCzhjbwOCB9OQTk4OmbFsuGccO/TcUe4JVMlj1w6qMPbH2ijp.fGy	Gerente	Prueba	0976787887	t	2026-02-04 22:14:39.117869+00	\N
4	1	prueba@vendedor	$2b$12$a0hHoZy0bsY3lrqudD/hr.OiWVABhhFkdxUuaibAJ6t6xJUlPP7Yq	Prueba	Vendedor		t	2026-02-06 20:46:18.308508+00	\N
5	1	usuario@prueba	$2b$12$sLAn8R1Axvh9rX5Fm4ZrEeuKoiMvC1Z.hllbVWHM79loXcrCjuLsO	Usuario	Temporal		t	2026-02-20 16:39:08.86179+00	\N
\.


--
-- Data for Name: vehiculos; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.vehiculos (id, empresa_id, tipo, chapa, vencimiento_habilitacion, vencimiento_cedula_verde) FROM stdin;
1	1	MOTO	ABC123	2026-02-12	2026-02-27
2	1	AUTOMOVIL	CBA321	2026-05-07	\N
3	1	CAMIONETA	BCA	\N	\N
\.


--
-- Data for Name: venta_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.venta_items (id, venta_id, producto_id, materia_laboratorio_id, cantidad, precio_unitario, total, observaciones) FROM stdin;
1	1	3	\N	3	85000.00	255000.00	\N
2	2	3	\N	1	85000.00	85000.00	\N
3	3	\N	2	1	90000.00	90000.00	\N
4	4	\N	2	1	90000.00	90000.00	\N
5	5	\N	2	1	90000.00	90000.00	\N
6	6	\N	1	1	500000.00	500000.00	\N
7	7	\N	1	1	500000.00	500000.00	\N
8	8	\N	1	1	430000.00	430000.00	\N
9	9	\N	1	1	500000.00	500000.00	\N
10	10	\N	1	1	500000.00	500000.00	\N
11	11	3	\N	2	85000.00	170000.00	\N
12	11	1	\N	2	60000.00	120000.00	\N
13	12	1	\N	1	60000.00	60000.00	\N
14	12	3	\N	1	85000.00	85000.00	\N
15	13	1	\N	1	60000.00	60000.00	\N
16	14	1	\N	1	60000.00	60000.00	\N
17	15	3	\N	4	85000.00	340000.00	\N
18	16	1	\N	1	60000.00	60000.00	\N
19	17	1	\N	1	60000.00	60000.00	\N
20	18	1	\N	1	60000.00	60000.00	\N
21	19	3	\N	1	85000.00	85000.00	\N
22	20	1	\N	2	60000.00	120000.00	\N
23	21	3	\N	3	85000.00	255000.00	\N
24	22	1	\N	3	60000.00	180000.00	\N
25	23	3	\N	1	85000.00	85000.00	\N
26	24	1	\N	2	60000.00	120000.00	\N
27	24	3	\N	1	85000.00	85000.00	\N
28	25	3	\N	1	85000.00	85000.00	\N
29	26	\N	3	1	430000.00	430000.00	\N
30	27	3	\N	1	85000.00	85000.00	\N
31	28	1	\N	1	60000.00	60000.00	\N
32	29	\N	3	1	430000.00	430000.00	\N
33	30	1	\N	1	60000.00	60000.00	\N
34	31	1	\N	2	60000.00	120000.00	\N
35	31	3	\N	3	85000.00	255000.00	\N
36	31	\N	3	1	430000.00	430000.00	\N
38	32	1	\N	1	60000.00	60000.00	\N
40	33	1	\N	1	60000.00	60000.00	\N
41	34	1	\N	1	60000.00	60000.00	\N
43	35	\N	3	1	430000.00	430000.00	\N
46	36	3	\N	1	85000.00	85000.00	\N
47	36	1	\N	2	60000.00	120000.00	\N
48	37	1	\N	1	60000.00	60000.00	\N
49	37	3	\N	1	85000.00	85000.00	\N
50	38	1	\N	1	60000.00	60000.00	\N
51	39	1	\N	1	60000.00	60000.00	\N
52	40	1	\N	2	60000.00	120000.00	\N
54	41	3	\N	1	85000.00	85000.00	\N
55	42	1	\N	1	60000.00	60000.00	\N
57	43	1	\N	1	60000.00	60000.00	\N
58	43	3	\N	2	85000.00	170000.00	\N
59	44	3	\N	1	85000.00	85000.00	\N
60	44	1	\N	1	60000.00	60000.00	\N
62	45	3	\N	1	85000.00	85000.00	\N
63	46	3	\N	1	85000.00	85000.00	\N
64	46	1	\N	2	60000.00	120000.00	\N
65	47	3	\N	1	85000.00	85000.00	\N
66	48	1	\N	1	60000.00	60000.00	\N
67	49	1	\N	2	60000.00	120000.00	\N
68	50	\N	4	1	40000.00	40000.00	\N
70	51	3	\N	1	85000.00	85000.00	\N
71	52	3	\N	1	85000.00	85000.00	\N
72	53	3	\N	2	85000.00	170000.00	\N
73	54	3	\N	4	85000.00	340000.00	\N
76	55	3	\N	1	85000.00	85000.00	\N
77	55	1	\N	1	60000.00	60000.00	\N
78	56	3	\N	1	85000.00	85000.00	\N
79	56	1	\N	1	60000.00	60000.00	\N
80	56	11	\N	1	2000.00	2000.00	\N
81	56	6	\N	1	1000.00	1000.00	\N
82	56	12	\N	1	2300.00	2300.00	\N
83	56	13	\N	1	1250.00	1250.00	\N
84	56	14	\N	1	3500.00	3500.00	\N
85	56	15	\N	1	1670.00	1670.00	\N
86	56	16	\N	1	4000.00	4000.00	\N
87	56	17	\N	1	8000.00	8000.00	\N
88	57	11	\N	1	2000.00	2000.00	\N
89	57	6	\N	1	1000.00	1000.00	\N
90	57	12	\N	1	2300.00	2300.00	\N
91	58	14	\N	1	3500.00	3500.00	\N
92	58	15	\N	1	1670.00	1670.00	\N
93	59	11	\N	1	2000.00	2000.00	\N
94	59	6	\N	1	1000.00	1000.00	\N
95	60	6	\N	1	1000.00	1000.00	\N
96	60	12	\N	1	2300.00	2300.00	\N
97	61	11	\N	1	2000.00	2000.00	\N
98	61	6	\N	1	1000.00	1000.00	\N
99	61	12	\N	1	2300.00	2300.00	\N
100	61	13	\N	1	1250.00	1250.00	\N
101	62	11	\N	1	2000.00	2000.00	\N
102	62	6	\N	1	1000.00	1000.00	\N
103	62	12	\N	1	2300.00	2300.00	\N
104	62	13	\N	1	1250.00	1250.00	\N
105	62	17	\N	1	8000.00	8000.00	\N
106	62	16	\N	1	4000.00	4000.00	\N
107	62	15	\N	1	1670.00	1670.00	\N
108	62	14	\N	1	3500.00	3500.00	\N
109	63	11	\N	1	2000.00	2000.00	\N
110	63	6	\N	1	1000.00	1000.00	\N
111	63	12	\N	1	2300.00	2300.00	\N
112	63	13	\N	1	1250.00	1250.00	\N
113	63	14	\N	1	3500.00	3500.00	\N
114	63	15	\N	1	1670.00	1670.00	\N
115	63	16	\N	1	4000.00	4000.00	\N
116	63	17	\N	1	8000.00	8000.00	\N
117	63	18	\N	1	4030.00	4030.00	\N
118	63	3	\N	1	85000.00	85000.00	\N
\.


--
-- Data for Name: ventas; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ventas (id, empresa_id, cliente_id, usuario_id, representante_cliente_id, total, iva, descuento, tipo_pago, es_delivery, estado, creado_en) FROM stdin;
1	1	2	1	\N	255000.00	23181.82	0.00	EFECTIVO	t	CONFIRMADA	2026-02-03 14:55:35.523441+00
2	1	1	1	\N	72250.00	6568.18	12750.00	CREDITO	f	CONFIRMADA	2026-02-03 16:43:20.233567+00
3	1	1	1	\N	76500.00	6954.55	13500.00	CREDITO	t	BORRADOR	2026-02-04 00:43:33.312855+00
4	1	1	1	\N	76500.00	6954.55	13500.00	CREDITO	t	BORRADOR	2026-02-04 00:43:37.237593+00
31	1	1	1	\N	684250.00	62204.55	120750.00	TARJETA	t	ANULADA	2026-02-05 20:54:43.111486+00
5	1	1	1	\N	76500.00	6954.55	13500.00	CREDITO	f	CONFIRMADA	2026-02-04 00:43:41.344414+00
6	1	1	1	\N	425000.00	38636.36	75000.00	EFECTIVO	t	BORRADOR	2026-02-04 16:54:52.410532+00
7	1	1	1	\N	425000.00	38636.36	75000.00	EFECTIVO	t	BORRADOR	2026-02-04 17:06:30.529105+00
46	1	3	1	\N	184500.00	16772.73	20500.00	TARJETA	f	CONFIRMADA	2026-02-09 18:28:06.934832+00
8	1	1	1	\N	365500.00	33227.27	64500.00	EFECTIVO	t	BORRADOR	2026-02-04 17:17:45.439627+00
9	1	1	1	\N	425000.00	38636.36	75000.00	EFECTIVO	t	BORRADOR	2026-02-04 17:24:49.474116+00
32	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	f	CONFIRMADA	2026-02-05 21:46:34.507878+00
10	1	1	1	\N	425000.00	38636.36	75000.00	EFECTIVO	f	CONFIRMADA	2026-02-04 17:29:57.15092+00
47	1	3	1	\N	76500.00	6954.55	8500.00	CHEQUE	f	CONFIRMADA	2026-02-09 18:36:13.22478+00
13	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	t	ANULADA	2026-02-04 17:31:26.36908+00
12	1	2	1	1	123250.00	11204.55	21750.00	CREDITO	t	ANULADA	2026-02-04 17:30:42.102951+00
11	1	1	1	\N	246500.00	22409.09	43500.00	EFECTIVO	t	ANULADA	2026-02-04 17:30:13.565253+00
33	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	t	CONFIRMADA	2026-02-05 22:02:10.679945+00
14	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	t	ANULADA	2026-02-04 17:42:20.174729+00
15	1	1	1	\N	289000.00	26272.73	51000.00	CREDITO	f	ANULADA	2026-02-04 17:47:00.144613+00
34	1	2	1	\N	60000.00	5454.55	0.00	TARJETA	f	CONFIRMADA	2026-02-05 22:02:58.929951+00
17	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	t	ANULADA	2026-02-04 18:23:24.740594+00
16	1	1	1	\N	51000.00	4636.36	9000.00	CREDITO	t	ANULADA	2026-02-04 18:05:42.66323+00
48	1	3	1	\N	54000.00	4909.09	6000.00	TRANSFERENCIA	f	CONFIRMADA	2026-02-09 18:44:23.598375+00
19	1	2	1	1	72250.00	6568.18	12750.00	CREDITO	t	ANULADA	2026-02-04 18:35:26.909527+00
18	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	t	ANULADA	2026-02-04 18:35:04.910518+00
20	1	1	1	\N	102000.00	9272.73	18000.00	EFECTIVO	t	CONFIRMADA	2026-02-04 18:56:38.306286+00
35	1	1	1	\N	365500.00	33227.27	64500.00	CHEQUE	f	CONFIRMADA	2026-02-05 22:03:50.975154+00
21	1	2	1	\N	255000.00	23181.82	0.00	EFECTIVO	t	ANULADA	2026-02-04 19:09:41.585878+00
22	1	2	1	1	153000.00	13909.09	27000.00	CREDITO	t	ANULADA	2026-02-04 19:11:32.842041+00
49	1	3	1	\N	108000.00	9818.18	12000.00	TARJETA	f	CONFIRMADA	2026-02-09 18:53:48.027425+00
23	1	1	1	\N	72250.00	6568.18	12750.00	CREDITO	t	ANULADA	2026-02-04 19:43:16.106337+00
24	1	1	1	\N	174250.00	15840.91	30750.00	CREDITO	t	ANULADA	2026-02-04 19:50:55.730262+00
25	1	1	1	\N	72250.00	6568.18	12750.00	EFECTIVO	t	CONFIRMADA	2026-02-04 20:12:48.085357+00
36	1	1	1	\N	174250.00	15840.91	30750.00	CHEQUE	t	CONFIRMADA	2026-02-05 22:04:37.546402+00
26	1	1	1	\N	365500.00	33227.27	64500.00	CREDITO	t	ANULADA	2026-02-04 20:22:26.796778+00
27	1	1	1	\N	72250.00	6568.18	12750.00	CREDITO	t	CONFIRMADA	2026-02-04 20:26:19.029203+00
28	1	1	1	\N	51000.00	4636.36	9000.00	EFECTIVO	t	ANULADA	2026-02-04 21:18:05.882385+00
37	1	1	1	\N	123250.00	11204.55	21750.00	TARJETA	f	CONFIRMADA	2026-02-05 22:17:20.167609+00
29	1	1	1	\N	365500.00	33227.27	64500.00	EFECTIVO	t	ANULADA	2026-02-04 21:27:53.604037+00
30	1	1	1	\N	51000.00	4636.36	9000.00	CREDITO	t	CONFIRMADA	2026-02-05 20:40:04.078138+00
50	1	4	1	\N	40000.00	3636.36	0.00	TRANSFERENCIA	f	CONFIRMADA	2026-02-09 19:27:10.889564+00
38	1	1	1	\N	51000.00	4636.36	9000.00	CHEQUE	f	ANULADA	2026-02-05 23:11:19.034244+00
39	1	1	1	\N	51000.00	4636.36	9000.00	CHEQUE	f	CONFIRMADA	2026-02-06 19:13:47.297708+00
40	1	1	3	\N	102000.00	9272.73	18000.00	EFECTIVO	f	CONFIRMADA	2026-02-06 20:41:48.367703+00
41	1	2	3	\N	85000.00	7727.27	0.00	TARJETA	t	CONFIRMADA	2026-02-06 20:42:13.696584+00
42	1	1	1	\N	51000.00	4636.36	9000.00	TARJETA	t	CONFIRMADA	2026-02-06 21:19:22.022153+00
51	1	4	1	\N	85000.00	7727.27	0.00	TARJETA	f	CONFIRMADA	2026-02-09 21:10:43.450571+00
43	1	1	3	\N	195500.00	17772.73	34500.00	CHEQUE	t	CONFIRMADA	2026-02-06 21:29:56.429527+00
44	1	2	1	1	116000.00	10545.45	29000.00	EFECTIVO	t	CONFIRMADA	2026-02-07 14:01:23.063482+00
59	1	1	4	\N	2400.00	218.18	600.00	TARJETA	f	CONFIRMADA	2026-02-10 20:49:43.87882+00
45	1	3	1	\N	76500.00	6954.55	8500.00	TARJETA	t	CONFIRMADA	2026-02-09 17:57:28.524483+00
53	1	3	1	\N	153000.00	13909.09	17000.00	EFECTIVO	f	CONFIRMADA	2026-02-10 18:52:35.773673+00
54	1	3	1	\N	306000.00	27818.18	34000.00	EFECTIVO	f	CONFIRMADA	2026-02-10 19:00:26.644075+00
60	1	2	4	\N	3300.00	300.00	0.00	TRANSFERENCIA	t	CONFIRMADA	2026-02-10 20:54:12.738956+00
55	1	4	1	\N	145000.00	13181.82	0.00	TARJETA	t	CONFIRMADA	2026-02-10 19:03:20.894602+00
56	1	4	1	\N	168720.00	15338.18	0.00	TRANSFERENCIA	f	CONFIRMADA	2026-02-10 19:26:27.173095+00
52	1	3	1	\N	76500.00	6954.55	8500.00	EFECTIVO	f	ANULADA	2026-02-10 18:07:58.396857+00
57	1	3	4	\N	4770.00	433.64	530.00	EFECTIVO	t	CONFIRMADA	2026-02-10 20:36:49.656082+00
58	1	3	4	\N	4653.00	423.00	517.00	EFECTIVO	f	CONFIRMADA	2026-02-10 20:37:17.46689+00
61	1	3	3	\N	5895.00	535.91	655.00	TARJETA	f	CONFIRMADA	2026-02-15 23:28:53.929368+00
62	1	1	3	\N	18976.00	1725.09	4744.00	EFECTIVO	f	CONFIRMADA	2026-02-16 00:49:23.808039+00
63	1	3	3	\N	101475.00	9225.00	11275.00	TARJETA	f	CONFIRMADA	2026-02-16 00:57:37.055163+00
\.


--
-- Name: adelantos_salario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.adelantos_salario_id_seq', 1, true);


--
-- Name: almacenes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.almacenes_id_seq', 2, true);


--
-- Name: categorias_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.categorias_id_seq', 1, false);


--
-- Name: ciclos_salario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ciclos_salario_id_seq', 1, false);


--
-- Name: clientes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.clientes_id_seq', 4, true);


--
-- Name: creditos_clientes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.creditos_clientes_id_seq', 14, true);


--
-- Name: deudas_proveedores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.deudas_proveedores_id_seq', 2, true);


--
-- Name: documentos_electronicos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documentos_electronicos_id_seq', 1, false);


--
-- Name: documentos_temporales_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.documentos_temporales_id_seq', 7, true);


--
-- Name: empresas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.empresas_id_seq', 1, true);


--
-- Name: entregas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.entregas_id_seq', 40, true);


--
-- Name: facturas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.facturas_id_seq', 1, false);


--
-- Name: funcionarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.funcionarios_id_seq', 2, true);


--
-- Name: marcas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.marcas_id_seq', 4, true);


--
-- Name: materias_laboratorio_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.materias_laboratorio_id_seq', 6, true);


--
-- Name: movimientos_stock_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.movimientos_stock_id_seq', 123, true);


--
-- Name: pagos_creditos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.pagos_creditos_id_seq', 8, true);


--
-- Name: permisos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.permisos_id_seq', 81, true);


--
-- Name: preferencias_usuario_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.preferencias_usuario_id_seq', 2, true);


--
-- Name: productos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.productos_id_seq', 18, true);


--
-- Name: proveedor_productos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proveedor_productos_id_seq', 1, false);


--
-- Name: proveedores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.proveedores_id_seq', 2, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.roles_id_seq', 4, true);


--
-- Name: stock_actual_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.stock_actual_id_seq', 14, true);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.usuarios_id_seq', 5, true);


--
-- Name: vehiculos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.vehiculos_id_seq', 3, true);


--
-- Name: venta_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.venta_items_id_seq', 118, true);


--
-- Name: ventas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.ventas_id_seq', 63, true);


--
-- Name: adelantos_salario adelantos_salario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adelantos_salario
    ADD CONSTRAINT adelantos_salario_pkey PRIMARY KEY (id);


--
-- Name: almacenes almacenes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.almacenes
    ADD CONSTRAINT almacenes_pkey PRIMARY KEY (id);


--
-- Name: categorias categorias_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categorias
    ADD CONSTRAINT categorias_pkey PRIMARY KEY (id);


--
-- Name: ciclos_salario ciclos_salario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ciclos_salario
    ADD CONSTRAINT ciclos_salario_pkey PRIMARY KEY (id);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);


--
-- Name: creditos_clientes creditos_clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creditos_clientes
    ADD CONSTRAINT creditos_clientes_pkey PRIMARY KEY (id);


--
-- Name: deudas_proveedores deudas_proveedores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deudas_proveedores
    ADD CONSTRAINT deudas_proveedores_pkey PRIMARY KEY (id);


--
-- Name: documentos_electronicos documentos_electronicos_factura_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_electronicos
    ADD CONSTRAINT documentos_electronicos_factura_id_key UNIQUE (factura_id);


--
-- Name: documentos_electronicos documentos_electronicos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_electronicos
    ADD CONSTRAINT documentos_electronicos_pkey PRIMARY KEY (id);


--
-- Name: documentos_temporales documentos_temporales_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_temporales
    ADD CONSTRAINT documentos_temporales_pkey PRIMARY KEY (id);


--
-- Name: empresas empresas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);


--
-- Name: empresas empresas_ruc_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_ruc_key UNIQUE (ruc);


--
-- Name: entregas entregas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entregas
    ADD CONSTRAINT entregas_pkey PRIMARY KEY (id);


--
-- Name: facturas facturas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT facturas_pkey PRIMARY KEY (id);


--
-- Name: facturas facturas_venta_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT facturas_venta_id_key UNIQUE (venta_id);


--
-- Name: funcionarios funcionarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.funcionarios
    ADD CONSTRAINT funcionarios_pkey PRIMARY KEY (id);


--
-- Name: marcas marcas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marcas
    ADD CONSTRAINT marcas_pkey PRIMARY KEY (id);


--
-- Name: materias_laboratorio materias_laboratorio_codigo_barra_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materias_laboratorio
    ADD CONSTRAINT materias_laboratorio_codigo_barra_key UNIQUE (codigo_barra);


--
-- Name: materias_laboratorio materias_laboratorio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materias_laboratorio
    ADD CONSTRAINT materias_laboratorio_pkey PRIMARY KEY (id);


--
-- Name: movimientos_stock movimientos_stock_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_stock
    ADD CONSTRAINT movimientos_stock_pkey PRIMARY KEY (id);


--
-- Name: pagos_creditos pagos_creditos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_creditos
    ADD CONSTRAINT pagos_creditos_pkey PRIMARY KEY (id);


--
-- Name: permisos permisos_clave_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_clave_key UNIQUE (clave);


--
-- Name: permisos permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permisos
    ADD CONSTRAINT permisos_pkey PRIMARY KEY (id);


--
-- Name: preferencias_usuario preferencias_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencias_usuario
    ADD CONSTRAINT preferencias_usuario_pkey PRIMARY KEY (id);


--
-- Name: preferencias_usuario preferencias_usuario_usuario_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencias_usuario
    ADD CONSTRAINT preferencias_usuario_usuario_id_key UNIQUE (usuario_id);


--
-- Name: productos productos_codigo_barra_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_codigo_barra_key UNIQUE (codigo_barra);


--
-- Name: productos productos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_pkey PRIMARY KEY (id);


--
-- Name: proveedor_productos proveedor_productos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor_productos
    ADD CONSTRAINT proveedor_productos_pkey PRIMARY KEY (id);


--
-- Name: proveedores proveedores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_pkey PRIMARY KEY (id);


--
-- Name: rol_permisos rol_permisos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permisos
    ADD CONSTRAINT rol_permisos_pkey PRIMARY KEY (rol_id, permiso_id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: stock_actual stock_actual_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_actual
    ADD CONSTRAINT stock_actual_pkey PRIMARY KEY (id);


--
-- Name: usuario_roles usuario_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT usuario_roles_pkey PRIMARY KEY (usuario_id, rol_id);


--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_email_key UNIQUE (email);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: vehiculos vehiculos_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehiculos
    ADD CONSTRAINT vehiculos_pkey PRIMARY KEY (id);


--
-- Name: venta_items venta_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_items
    ADD CONSTRAINT venta_items_pkey PRIMARY KEY (id);


--
-- Name: ventas ventas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas
    ADD CONSTRAINT ventas_pkey PRIMARY KEY (id);


--
-- Name: ix_adelantos_salario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_adelantos_salario_id ON public.adelantos_salario USING btree (id);


--
-- Name: ix_almacenes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_almacenes_id ON public.almacenes USING btree (id);


--
-- Name: ix_categorias_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_categorias_id ON public.categorias USING btree (id);


--
-- Name: ix_ciclos_salario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ciclos_salario_id ON public.ciclos_salario USING btree (id);


--
-- Name: ix_clientes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clientes_id ON public.clientes USING btree (id);


--
-- Name: ix_creditos_clientes_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_creditos_clientes_id ON public.creditos_clientes USING btree (id);


--
-- Name: ix_deudas_proveedores_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_deudas_proveedores_id ON public.deudas_proveedores USING btree (id);


--
-- Name: ix_documentos_electronicos_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_electronicos_id ON public.documentos_electronicos USING btree (id);


--
-- Name: ix_documentos_temporales_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documentos_temporales_id ON public.documentos_temporales USING btree (id);


--
-- Name: ix_documentos_temporales_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_documentos_temporales_token ON public.documentos_temporales USING btree (token);


--
-- Name: ix_empresas_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_empresas_id ON public.empresas USING btree (id);


--
-- Name: ix_entregas_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_entregas_id ON public.entregas USING btree (id);


--
-- Name: ix_facturas_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_facturas_id ON public.facturas USING btree (id);


--
-- Name: ix_funcionarios_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_funcionarios_id ON public.funcionarios USING btree (id);


--
-- Name: ix_marcas_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_marcas_id ON public.marcas USING btree (id);


--
-- Name: ix_materias_laboratorio_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_materias_laboratorio_id ON public.materias_laboratorio USING btree (id);


--
-- Name: ix_movimientos_stock_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movimientos_stock_id ON public.movimientos_stock USING btree (id);


--
-- Name: ix_pagos_creditos_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pagos_creditos_id ON public.pagos_creditos USING btree (id);


--
-- Name: ix_permisos_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_permisos_id ON public.permisos USING btree (id);


--
-- Name: ix_preferencias_usuario_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_preferencias_usuario_id ON public.preferencias_usuario USING btree (id);


--
-- Name: ix_productos_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_productos_id ON public.productos USING btree (id);


--
-- Name: ix_proveedor_productos_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proveedor_productos_id ON public.proveedor_productos USING btree (id);


--
-- Name: ix_proveedores_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proveedores_id ON public.proveedores USING btree (id);


--
-- Name: ix_roles_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_roles_id ON public.roles USING btree (id);


--
-- Name: ix_stock_actual_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stock_actual_id ON public.stock_actual USING btree (id);


--
-- Name: ix_usuarios_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usuarios_id ON public.usuarios USING btree (id);


--
-- Name: ix_vehiculos_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vehiculos_id ON public.vehiculos USING btree (id);


--
-- Name: ix_venta_items_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_venta_items_id ON public.venta_items USING btree (id);


--
-- Name: ix_ventas_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ventas_id ON public.ventas USING btree (id);


--
-- Name: adelantos_salario adelantos_salario_funcionario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.adelantos_salario
    ADD CONSTRAINT adelantos_salario_funcionario_id_fkey FOREIGN KEY (funcionario_id) REFERENCES public.funcionarios(id);


--
-- Name: almacenes almacenes_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.almacenes
    ADD CONSTRAINT almacenes_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: categorias categorias_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categorias
    ADD CONSTRAINT categorias_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: ciclos_salario ciclos_salario_funcionario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ciclos_salario
    ADD CONSTRAINT ciclos_salario_funcionario_id_fkey FOREIGN KEY (funcionario_id) REFERENCES public.funcionarios(id);


--
-- Name: clientes clientes_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: creditos_clientes creditos_clientes_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creditos_clientes
    ADD CONSTRAINT creditos_clientes_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: creditos_clientes creditos_clientes_venta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.creditos_clientes
    ADD CONSTRAINT creditos_clientes_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id);


--
-- Name: deudas_proveedores deudas_proveedores_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deudas_proveedores
    ADD CONSTRAINT deudas_proveedores_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.proveedores(id);


--
-- Name: documentos_electronicos documentos_electronicos_factura_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_electronicos
    ADD CONSTRAINT documentos_electronicos_factura_id_fkey FOREIGN KEY (factura_id) REFERENCES public.facturas(id);


--
-- Name: documentos_temporales documentos_temporales_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_temporales
    ADD CONSTRAINT documentos_temporales_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: documentos_temporales documentos_temporales_venta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentos_temporales
    ADD CONSTRAINT documentos_temporales_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id);


--
-- Name: entregas entregas_responsable_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entregas
    ADD CONSTRAINT entregas_responsable_usuario_id_fkey FOREIGN KEY (responsable_usuario_id) REFERENCES public.usuarios(id);


--
-- Name: entregas entregas_vehiculo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entregas
    ADD CONSTRAINT entregas_vehiculo_id_fkey FOREIGN KEY (vehiculo_id) REFERENCES public.vehiculos(id);


--
-- Name: entregas entregas_venta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entregas
    ADD CONSTRAINT entregas_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id);


--
-- Name: facturas facturas_venta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facturas
    ADD CONSTRAINT facturas_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id);


--
-- Name: funcionarios funcionarios_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.funcionarios
    ADD CONSTRAINT funcionarios_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: marcas marcas_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marcas
    ADD CONSTRAINT marcas_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: materias_laboratorio materias_laboratorio_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.materias_laboratorio
    ADD CONSTRAINT materias_laboratorio_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: movimientos_stock movimientos_stock_almacen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_stock
    ADD CONSTRAINT movimientos_stock_almacen_id_fkey FOREIGN KEY (almacen_id) REFERENCES public.almacenes(id);


--
-- Name: movimientos_stock movimientos_stock_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimientos_stock
    ADD CONSTRAINT movimientos_stock_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: pagos_creditos pagos_creditos_credito_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pagos_creditos
    ADD CONSTRAINT pagos_creditos_credito_id_fkey FOREIGN KEY (credito_id) REFERENCES public.creditos_clientes(id);


--
-- Name: preferencias_usuario preferencias_usuario_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preferencias_usuario
    ADD CONSTRAINT preferencias_usuario_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: productos productos_categoria_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_categoria_id_fkey FOREIGN KEY (categoria_id) REFERENCES public.categorias(id);


--
-- Name: productos productos_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: productos productos_marca_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productos
    ADD CONSTRAINT productos_marca_id_fkey FOREIGN KEY (marca_id) REFERENCES public.marcas(id);


--
-- Name: proveedor_productos proveedor_productos_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor_productos
    ADD CONSTRAINT proveedor_productos_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: proveedor_productos proveedor_productos_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor_productos
    ADD CONSTRAINT proveedor_productos_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.proveedores(id);


--
-- Name: proveedores proveedores_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedores
    ADD CONSTRAINT proveedores_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: rol_permisos rol_permisos_permiso_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permisos
    ADD CONSTRAINT rol_permisos_permiso_id_fkey FOREIGN KEY (permiso_id) REFERENCES public.permisos(id);


--
-- Name: rol_permisos rol_permisos_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_permisos
    ADD CONSTRAINT rol_permisos_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.roles(id);


--
-- Name: roles roles_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: stock_actual stock_actual_almacen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_actual
    ADD CONSTRAINT stock_actual_almacen_id_fkey FOREIGN KEY (almacen_id) REFERENCES public.almacenes(id);


--
-- Name: stock_actual stock_actual_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stock_actual
    ADD CONSTRAINT stock_actual_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: usuario_roles usuario_roles_rol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT usuario_roles_rol_id_fkey FOREIGN KEY (rol_id) REFERENCES public.roles(id);


--
-- Name: usuario_roles usuario_roles_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_roles
    ADD CONSTRAINT usuario_roles_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- Name: usuarios usuarios_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: vehiculos vehiculos_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehiculos
    ADD CONSTRAINT vehiculos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: venta_items venta_items_materia_laboratorio_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_items
    ADD CONSTRAINT venta_items_materia_laboratorio_id_fkey FOREIGN KEY (materia_laboratorio_id) REFERENCES public.materias_laboratorio(id);


--
-- Name: venta_items venta_items_producto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_items
    ADD CONSTRAINT venta_items_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.productos(id);


--
-- Name: venta_items venta_items_venta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_items
    ADD CONSTRAINT venta_items_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id);


--
-- Name: ventas ventas_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas
    ADD CONSTRAINT ventas_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id);


--
-- Name: ventas ventas_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas
    ADD CONSTRAINT ventas_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id);


--
-- Name: ventas ventas_representante_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas
    ADD CONSTRAINT ventas_representante_cliente_id_fkey FOREIGN KEY (representante_cliente_id) REFERENCES public.clientes(id);


--
-- Name: ventas ventas_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ventas
    ADD CONSTRAINT ventas_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id);


--
-- PostgreSQL database dump complete
--

\unrestrict sLHgbc5Wwlu2164XOveSt4MTk7cpyVXQcR7Mmo6OI3p1cFI1gBNWtavsoZ15gHx

