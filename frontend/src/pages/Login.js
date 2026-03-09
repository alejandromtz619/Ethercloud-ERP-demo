import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';

const getInitials = (nombre) => {
  if (!nombre) return '?';
  const words = nombre.trim().split(/\s+/);
  if (words.length === 1) return words[0].substring(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
};

const Login = () => {
  const { login, API_URL } = useApp();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [empresa, setEmpresa] = useState(null);
  const [logoError, setLogoError] = useState(false);

  useEffect(() => {
    const fetchEmpresa = async () => {
      try {
        const res = await fetch(`${API_URL}/empresas/1`);
        if (res.ok) {
          const data = await res.json();
          setEmpresa(data);
          setLogoError(false);
        }
      } catch (_) {}
    };
    fetchEmpresa();
  }, [API_URL]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error('Por favor complete todos los campos');
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      toast.success('¡Bienvenido!');
      navigate('/home');
    } catch (err) {
      toast.error(err.message || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-4 bg-cover bg-center"
      style={{
        backgroundImage: "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.7)), url('/lago-republica.jpg')"
      }}
    >
      <Card className="w-full max-w-md shadow-2xl" style={{ backgroundColor: 'white' }} data-testid="login-card">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 rounded-xl bg-primary flex items-center justify-center mb-4 overflow-hidden">
            {empresa?.logo_url && !logoError ? (
              <img src={empresa.logo_url} alt={empresa.nombre} className="w-full h-full object-contain p-1" onError={() => setLogoError(true)} />
            ) : (
              <span className="text-2xl font-bold text-white tracking-tight">
                {empresa ? getInitials(empresa.nombre) : '?'}
              </span>
            )}
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">
            {empresa ? empresa.nombre : 'Cargando...'}
          </CardTitle>
          <CardDescription className="text-gray-600">Ingrese sus credenciales para continuar</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-700">Correo electrónico</Label>
              <Input
                id="email"
                type="email"
                placeholder="usuario@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                data-testid="login-email"
                className="bg-white text-gray-900"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-gray-700">Contraseña</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                  data-testid="login-password"
                  className="bg-white text-gray-900"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <Button 
              type="submit" 
              className="w-full" 
              disabled={loading}
              data-testid="login-submit"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Ingresando...
                </>
              ) : (
                'Ingresar'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
