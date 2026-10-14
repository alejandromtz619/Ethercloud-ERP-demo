"""
Test suite for Ethercloud ERP - Permissions and Historial Ventas features
Tests:
1. Permission system - Admin sees all modules
2. Permission system - User without role sees restricted modules
3. Historial Ventas - Page loads and shows ventas
4. Historial Ventas - Filters work
5. Print Modal - Boleta endpoint
6. Print Modal - Factura endpoint
7. Print Modal - Opens after confirming venta (integration)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://enterprise-luz.preview.emergentagent.com')
if not BASE_URL.endswith('/api'):
    BASE_URL = BASE_URL.rstrip('/') + '/api'


class TestPermissionSystem:
    """Tests for the permission system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@ether.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        data = login_resp.json()
        self.admin_token = data.get("access_token")
        self.admin_user = data.get("usuario", {})
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_admin_has_permissions(self):
        """Test 1: Admin user has all permissions"""
        resp = requests.get(
            f"{BASE_URL}/usuarios/{self.admin_user.get('id')}/permisos",
            headers=self.headers
        )
        assert resp.status_code == 200
        permisos = resp.json()
        assert len(permisos) > 0, "Admin should have permissions"
        assert len(permisos) >= 50, f"Admin should have many permissions, got {len(permisos)}"
        
        # Check for specific permissions
        permission_keys = [p.get('clave') for p in permisos]
        assert 'ventas.crear' in permission_keys
        assert 'ventas.ver_historial' in permission_keys
        assert 'usuarios.gestionar' in permission_keys
    
    def test_user_without_role_has_no_permissions(self):
        """Test 2: User without role has no permissions"""
        # Create test user without role
        test_email = f"TEST_norol_{os.urandom(4).hex()}@ether.com"
        create_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": test_email,
            "password": "test123",
            "nombre": "Test",
            "apellido": "NoRol",
            "empresa_id": 1
        })
        
        if create_resp.status_code == 200:
            new_user = create_resp.json()
            new_user_id = new_user.get("usuario", {}).get("id")
            
            # Get permissions for user without role
            permisos_resp = requests.get(
                f"{BASE_URL}/usuarios/{new_user_id}/permisos",
                headers=self.headers
            )
            assert permisos_resp.status_code == 200
            permisos = permisos_resp.json()
            assert len(permisos) == 0, f"User without role should have 0 permissions, got {len(permisos)}"


class TestHistorialVentas:
    """Tests for Historial Ventas functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@ether.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        data = login_resp.json()
        self.token = data.get("access_token")
        self.user = data.get("usuario", {})
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_ventas_list_endpoint(self):
        """Test 3: Ventas list endpoint works"""
        resp = requests.get(
            f"{BASE_URL}/ventas?empresa_id=1",
            headers=self.headers
        )
        assert resp.status_code == 200
        ventas = resp.json()
        assert isinstance(ventas, list)
    
    def test_ventas_filters(self):
        """Test 4: Ventas filters work"""
        # Test with date filter
        resp = requests.get(
            f"{BASE_URL}/ventas?empresa_id=1&fecha_desde=2026-01-01",
            headers=self.headers
        )
        assert resp.status_code == 200
        
        # Test with monto filter
        resp = requests.get(
            f"{BASE_URL}/ventas?empresa_id=1&monto_min=0&monto_max=1000000",
            headers=self.headers
        )
        assert resp.status_code == 200


class TestPrintModal:
    """Tests for Print Modal (Boleta/Factura) functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and ensure we have a venta to test"""
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@ether.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        data = login_resp.json()
        self.token = data.get("access_token")
        self.user = data.get("usuario", {})
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get existing ventas
        ventas_resp = requests.get(
            f"{BASE_URL}/ventas?empresa_id=1",
            headers=self.headers
        )
        ventas = ventas_resp.json()
        if ventas:
            self.venta_id = ventas[0].get("id")
        else:
            self.venta_id = None
    
    def test_boleta_endpoint(self):
        """Test 5: Boleta endpoint returns correct data"""
        if not self.venta_id:
            pytest.skip("No ventas available to test")
        
        resp = requests.get(
            f"{BASE_URL}/ventas/{self.venta_id}/boleta",
            headers=self.headers
        )
        assert resp.status_code == 200
        boleta = resp.json()
        
        # Verify boleta structure
        assert boleta.get('tipo') == 'BOLETA'
        assert 'numero' in boleta
        assert 'fecha' in boleta
        assert 'cliente' in boleta
        assert 'items' in boleta
        assert 'total' in boleta
        assert 'total_letras' in boleta
    
    def test_factura_endpoint(self):
        """Test 6: Factura endpoint returns correct data"""
        if not self.venta_id:
            pytest.skip("No ventas available to test")
        
        resp = requests.get(
            f"{BASE_URL}/ventas/{self.venta_id}/factura",
            headers=self.headers
        )
        # Factura may fail if client has no RUC
        if resp.status_code == 200:
            factura = resp.json()
            assert factura.get('tipo') == 'FACTURA'
            assert 'numero' in factura
            assert 'fecha' in factura
            assert 'cliente' in factura
            assert 'items' in factura
            assert 'total' in factura
        elif resp.status_code == 400:
            # Expected if client has no RUC
            assert "RUC" in resp.text
    
    def test_create_venta_and_confirm(self):
        """Test 7: Create and confirm venta (integration test)"""
        # Get a client
        clientes_resp = requests.get(
            f"{BASE_URL}/clientes?empresa_id=1",
            headers=self.headers
        )
        clientes = clientes_resp.json()
        if not clientes:
            pytest.skip("No clients available")
        cliente_id = clientes[0].get("id")
        
        # Get a product
        productos_resp = requests.get(
            f"{BASE_URL}/productos?empresa_id=1",
            headers=self.headers
        )
        productos = productos_resp.json()
        if not productos:
            pytest.skip("No products available")
        producto = productos[0]
        producto_id = producto.get("id")
        
        # Create venta
        venta_data = {
            "empresa_id": 1,
            "cliente_id": cliente_id,
            "usuario_id": self.user.get("id"),
            "tipo_pago": "EFECTIVO",
            "es_delivery": False,
            "items": [{
                "producto_id": producto_id,
                "cantidad": 1,
                "precio_unitario": producto.get("precio_venta", 50000)
            }]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/ventas",
            json=venta_data,
            headers=self.headers
        )
        assert create_resp.status_code == 200, f"Create venta failed: {create_resp.text}"
        venta = create_resp.json()
        venta_id = venta.get("id")
        
        # Confirm venta
        confirm_resp = requests.post(
            f"{BASE_URL}/ventas/{venta_id}/confirmar",
            headers=self.headers
        )
        assert confirm_resp.status_code == 200, f"Confirm venta failed: {confirm_resp.text}"
        
        # Verify boleta is available
        boleta_resp = requests.get(
            f"{BASE_URL}/ventas/{venta_id}/boleta",
            headers=self.headers
        )
        assert boleta_resp.status_code == 200
        boleta = boleta_resp.json()
        assert boleta.get('numero') == venta_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
