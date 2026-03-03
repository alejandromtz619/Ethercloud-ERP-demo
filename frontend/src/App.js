import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from './context/AppContext';
import { Toaster } from './components/ui/sonner';
import Layout from './components/Layout';

// Pages
import Login from './pages/Login';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Ventas from './pages/Ventas';
import Delivery from './pages/Delivery';
import Laboratorio from './pages/Laboratorio';
import Productos from './pages/Productos';
import Proveedores from './pages/Proveedores';
import Clientes from './pages/Clientes';
import Funcionarios from './pages/Funcionarios';
import Stock from './pages/Stock';
import Flota from './pages/Flota';
import Facturas from './pages/Facturas';
import Usuarios from './pages/Usuarios';
import Sistema from './pages/Sistema';
import Marcas from './pages/Marcas';
import Categorias from './pages/Categorias';
import Permisos from './pages/Permisos';
import HistorialVentas from './pages/HistorialVentas';
import Reportes from './pages/Reportes';

import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, permission }) => {
  const { user, loading, hasPermission } = useApp();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  // Validar permiso si se especifica
  if (permission) {
    // Si permission es array, verificar si tiene al menos uno
    if (Array.isArray(permission)) {
      const hasAnyPermission = permission.some(perm => hasPermission(perm));
      if (!hasAnyPermission) {
        return <Navigate to="/home" replace />;
      }
    } else {
      // Si es string, verificar ese permiso
      if (!hasPermission(permission)) {
        return <Navigate to="/home" replace />;
      }
    }
  }
  
  return children;
};

// Routes with Layout
const AppRoutes = () => {
  const { user } = useApp();
  
  return (
    <Routes>
      {/* Public Routes */}
      <Route 
        path="/login" 
        element={user ? <Navigate to="/home" replace /> : <Login />} 
      />
      
      {/* Protected Routes */}
      <Route 
        path="/home" 
        element={
          <ProtectedRoute>
            <Home />
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute permission="dashboard.ver">
            <Layout>
              <Dashboard />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/ventas" 
        element={
          <ProtectedRoute permission={['ventas.crear', 'ventas.ver']}>
            <Layout>
              <Ventas />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/delivery" 
        element={
          <ProtectedRoute permission="delivery.ver">
            <Layout>
              <Delivery />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/historial-ventas" 
        element={
          <ProtectedRoute permission="ventas.ver_historial">
            <Layout>
              <HistorialVentas />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/laboratorio" 
        element={
          <ProtectedRoute permission="laboratorio.ver">
            <Layout>
              <Laboratorio />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/productos" 
        element={
          <ProtectedRoute permission="productos.ver">
            <Layout>
              <Productos />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/proveedores" 
        element={
          <ProtectedRoute permission="proveedores.ver">
            <Layout>
              <Proveedores />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/clientes" 
        element={
          <ProtectedRoute permission="clientes.ver">
            <Layout>
              <Clientes />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/funcionarios" 
        element={
          <ProtectedRoute permission="funcionarios.ver">
            <Layout>
              <Funcionarios />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/stock" 
        element={
          <ProtectedRoute permission="stock.ver">
            <Layout>
              <Stock />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/flota" 
        element={
          <ProtectedRoute permission="flota.ver">
            <Layout>
              <Flota />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/facturas" 
        element={
          <ProtectedRoute permission="facturas.ver">
            <Layout>
              <Facturas />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/usuarios" 
        element={
          <ProtectedRoute permission="usuarios.ver">
            <Layout>
              <Usuarios />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/marcas" 
        element={
          <ProtectedRoute permission="productos.ver">
            <Layout>
              <Marcas />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/categorias" 
        element={
          <ProtectedRoute permission="productos.ver">
            <Layout>
              <Categorias />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/permisos" 
        element={
          <ProtectedRoute permission="roles.gestionar">
            <Layout>
              <Permisos />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/reportes" 
        element={
          <ProtectedRoute permission="reportes.ver">
            <Layout>
              <Reportes />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      <Route 
        path="/sistema" 
        element={
          <ProtectedRoute permission="sistema.configurar">
            <Layout>
              <Sistema />
            </Layout>
          </ProtectedRoute>
        } 
      />
      
      {/* Default Route */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <AppRoutes />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
