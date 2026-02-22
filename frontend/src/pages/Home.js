import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { LayoutDashboard, ShoppingCart, Truck, LogOut } from 'lucide-react';

const Home = () => {
  const { user, empresa, userPermisos, logout } = useApp();
  const navigate = useNavigate();

  const mainModules = [
    {
      id: 'dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
      title: 'Dashboard',
      description: 'Estadísticas, gráficos y alertas del sistema',
      color: 'from-blue-500 to-blue-600',
      permission: 'dashboard.ver'
    },
    {
      id: 'ventas',
      path: '/ventas',
      icon: ShoppingCart,
      title: 'Ventas',
      description: 'Crear y gestionar ventas, facturación',
      color: 'from-green-500 to-green-600',
      permission: ['ventas.crear', 'ventas.ver'] // Acepta cualquiera de estos
    },
    {
      id: 'delivery',
      path: '/delivery',
      icon: Truck,
      title: 'Delivery',
      description: 'Gestión de entregas y pedidos',
      color: 'from-orange-500 to-orange-600',
      permission: 'delivery.ver'
    }
  ];

  // Filter modules by user permissions
  const visibleModules = mainModules.filter(module => {
    if (!module.permission) return true; // No permission required
    
    // Si permission es array, verificar si tiene al menos uno
    if (Array.isArray(module.permission)) {
      return module.permission.some(perm => userPermisos.includes(perm));
    }
    
    // Si es string, verificar ese permiso
    return userPermisos.includes(module.permission);
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4 sm:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Welcome Header */}
        <div className="text-center mb-12 relative">
          {/* Logout button */}
          <Button
            variant="outline"
            size="sm"
            onClick={logout}
            className="absolute top-0 right-0"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Cerrar Sesión
          </Button>
          
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-primary mb-6">
            {empresa?.logo_url ? (
              <img src={empresa.logo_url} alt={empresa.nombre} className="w-full h-full object-contain p-3" />
            ) : (
              <span className="text-3xl font-bold text-white font-['Manrope']">
                {empresa?.nombre?.substring(0, 2).toUpperCase() || 'LB'}
              </span>
            )}
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold mb-2">
            ¡Bienvenido, {user?.nombre}!
          </h1>
          <p className="text-muted-foreground text-lg">
            {empresa?.nombre || 'Luz Brill ERP'}
          </p>
        </div>

        {/* Main Modules Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {visibleModules.map((module) => (
            <Card 
              key={module.id}
              className="group cursor-pointer overflow-hidden hover:shadow-xl transition-all duration-300"
              onClick={() => navigate(module.path)}
              data-testid={`home-btn-${module.id}`}
            >
              <CardContent className="p-0">
                <div className={`bg-gradient-to-br ${module.color} p-8 text-white`}>
                  <module.icon className="h-12 w-12 mb-4 group-hover:scale-110 transition-transform" />
                  <h2 className="text-2xl font-bold mb-2">{module.title}</h2>
                  <p className="text-white/80 text-sm">{module.description}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Quick Info */}
        <div className="mt-12 text-center text-muted-foreground text-sm">
          {visibleModules.length > 0 ? (
            <p>Seleccione un módulo para comenzar</p>
          ) : (
            <p>No tienes acceso a ningún módulo principal. Contacta al administrador.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Home;
