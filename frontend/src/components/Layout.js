import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { 
  LayoutDashboard, ShoppingCart, Truck, Package, Users, Building2, 
  FlaskConical, Warehouse, Car, FileText, Settings, UserCog, LogOut,
  Menu, X, ChevronDown, Sun, Moon, Tag, Shield, History, FileBarChart
} from 'lucide-react';
import Clock from './Clock';
import { Button } from '../components/ui/button';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '../components/ui/dropdown-menu';
import { cn } from '../lib/utils';

const allMenuItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/ventas', icon: ShoppingCart, label: 'Ventas' },
  { path: '/historial-ventas', icon: History, label: 'Historial Ventas' },
  { path: '/delivery', icon: Truck, label: 'Delivery' },
  { path: '/laboratorio', icon: FlaskConical, label: 'Laboratorio' },
  { path: '/productos', icon: Package, label: 'Productos' },
  { path: '/marcas', icon: Tag, label: 'Marcas' },
  { path: '/proveedores', icon: Building2, label: 'Proveedores' },
  { path: '/clientes', icon: Users, label: 'Clientes' },
  { path: '/funcionarios', icon: UserCog, label: 'Funcionarios' },
  { path: '/stock', icon: Warehouse, label: 'Stock' },
  { path: '/flota', icon: Car, label: 'Flota' },
  { path: '/facturas', icon: FileText, label: 'Facturas' },
  { path: '/reportes', icon: FileBarChart, label: 'Reportes' },
  { path: '/usuarios', icon: Users, label: 'Usuarios' },
  { path: '/permisos', icon: Shield, label: 'Permisos' },
  { path: '/sistema', icon: Settings, label: 'Sistema' },
];

const Layout = ({ children }) => {
  const { user, empresa, logout, theme, setTheme, canAccessRoute } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  // Filter menu items based on user permissions
  const menuItems = allMenuItems.filter(item => canAccessRoute(item.path));

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Mobile bottom nav items
  const mobileNavItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/ventas', icon: ShoppingCart, label: 'Ventas' },
    { path: '/delivery', icon: Truck, label: 'Delivery' },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 z-40 h-screen w-64 bg-neutral-900 text-white transition-transform lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-neutral-800">
          <div className="flex items-center gap-2">
            {empresa?.logo_url ? (
              <img src={empresa.logo_url} alt={empresa.nombre} className="w-8 h-8 object-contain" />
            ) : (
              <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
                <span className="font-bold text-white">
                  {empresa?.nombre?.substring(0, 2).toUpperCase() || 'LB'}
                </span>
              </div>
            )}
            <span className="font-bold text-lg font-['Manrope']">{empresa?.nombre || 'Luz Brill'}</span>
          </div>
          <Button 
            variant="ghost" 
            size="icon" 
            className="lg:hidden text-white hover:bg-neutral-800"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Nav */}
        <ScrollArea className="h-[calc(100vh-4rem)] py-4">
          <nav className="px-2 space-y-1">
            {menuItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                  isActive 
                    ? "bg-primary text-white" 
                    : "text-neutral-300 hover:bg-neutral-800 hover:text-white"
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </ScrollArea>
      </aside>

      {/* Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="lg:pl-64">
        {/* Header */}
        <header className="sticky top-0 z-20 h-16 bg-background border-b flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="hidden sm:block">
              <h1 className="font-semibold text-lg">{empresa?.nombre || 'Luz Brill ERP'}</h1>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Clock */}
            <div className="hidden md:block">
              <Clock />
            </div>

            <div className="flex items-center gap-2">
            {/* Theme toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              data-testid="theme-toggle"
            >
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>

            {/* User menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="flex items-center gap-2" data-testid="user-menu">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-sm font-medium text-primary">
                      {user?.nombre?.charAt(0) || 'U'}
                    </span>
                  </div>
                  <span className="hidden sm:block text-sm">{user?.nombre}</span>
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium">{user?.nombre} {user?.apellido}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate('/sistema')}>
                  <Settings className="mr-2 h-4 w-4" />
                  Configuración
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive" data-testid="logout-btn">
                  <LogOut className="mr-2 h-4 w-4" />
                  Cerrar sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-4 lg:p-6 pb-20 lg:pb-6">
          {children}
        </main>

        {/* Mobile Bottom Nav */}
        <nav className="mobile-nav lg:hidden flex items-center justify-around py-2 px-4">
          {mobileNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => cn(
                "flex flex-col items-center gap-1 py-1 px-3 rounded-lg transition-colors",
                isActive ? "text-primary" : "text-muted-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="text-xs">{item.label}</span>
            </NavLink>
          ))}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex flex-col items-center gap-1 py-1 px-3 text-muted-foreground">
                <Menu className="h-5 w-5" />
                <span className="text-xs">Más</span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {menuItems.slice(3).map((item) => (
                <DropdownMenuItem key={item.path} onClick={() => navigate(item.path)}>
                  <item.icon className="mr-2 h-4 w-4" />
                  {item.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>
      </div>
    </div>
  );
};

export default Layout;
