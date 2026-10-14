"""
Test suite for Ethercloud ERP - Créditos, Reportes PDF, and Ciclos Salario features
Tests:
1. Clientes: campo limite_credito se guarda y muestra
2. Clientes: crédito disponible endpoint
3. Clientes: lista de créditos pendientes
4. Clientes: pago parcial de crédito
5. Ventas a crédito: valida límite de crédito
6. Ventas a crédito: crea registro de crédito al confirmar
7. Reportes: 4 tipos de reportes PDF
8. Ciclos salario: generar ciclos
9. Ciclos salario: alertas pendientes
"""

import pytest
import requests
import os
from datetime import date, datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@ether.com"
TEST_PASSWORD = "admin123"
EMPRESA_ID = 1


class TestAuth:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "usuario" in data
        return data["access_token"]


class TestClientesCreditos:
    """Tests for cliente credit limit and credit management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_create_cliente_with_limite_credito(self):
        """Test 1: Create cliente with limite_credito field"""
        cliente_data = {
            "empresa_id": EMPRESA_ID,
            "nombre": "TEST_Cliente_Credito",
            "apellido": "Prueba",
            "ruc": "TEST123456-7",
            "telefono": "0981123456",
            "limite_credito": 5000000,  # 5 million Gs
            "descuento_porcentaje": 5
        }
        
        response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create cliente: {response.text}"
        
        data = response.json()
        # limite_credito may be returned as string or number
        limite = float(data["limite_credito"]) if isinstance(data["limite_credito"], str) else data["limite_credito"]
        assert limite == 5000000, f"limite_credito not saved correctly: {data['limite_credito']}"
        assert data["nombre"] == "TEST_Cliente_Credito"
        
        # Store cliente_id for later tests
        self.__class__.cliente_id = data["id"]
        print(f"Created cliente with id={data['id']}, limite_credito={data['limite_credito']}")
    
    def test_02_get_cliente_shows_limite_credito(self):
        """Test 1b: Verify limite_credito is returned in cliente list"""
        response = requests.get(f"{BASE_URL}/api/clientes?empresa_id={EMPRESA_ID}", headers=self.headers)
        assert response.status_code == 200
        
        clientes = response.json()
        test_cliente = next((c for c in clientes if c["nombre"] == "TEST_Cliente_Credito"), None)
        assert test_cliente is not None, "Test cliente not found in list"
        # limite_credito may be returned as string or number
        limite = float(test_cliente["limite_credito"]) if isinstance(test_cliente["limite_credito"], str) else test_cliente["limite_credito"]
        assert limite == 5000000, f"limite_credito not shown in table: {test_cliente['limite_credito']}"
        print(f"Cliente in list shows limite_credito={test_cliente['limite_credito']}")
    
    def test_03_get_credito_disponible(self):
        """Test 2: Get credit summary (limite, usado, disponible)"""
        cliente_id = getattr(self.__class__, 'cliente_id', None)
        if not cliente_id:
            pytest.skip("No cliente_id from previous test")
        
        response = requests.get(f"{BASE_URL}/api/clientes/{cliente_id}/credito-disponible", headers=self.headers)
        assert response.status_code == 200, f"Failed to get credito disponible: {response.text}"
        
        data = response.json()
        assert "limite_credito" in data
        assert "credito_usado" in data
        assert "credito_disponible" in data
        assert data["limite_credito"] == 5000000
        assert data["credito_usado"] == 0  # No credits yet
        assert data["credito_disponible"] == 5000000
        print(f"Credito disponible: limite={data['limite_credito']}, usado={data['credito_usado']}, disponible={data['credito_disponible']}")
    
    def test_04_create_credito_manual(self):
        """Test 3: Create a credit record manually"""
        cliente_id = getattr(self.__class__, 'cliente_id', None)
        if not cliente_id:
            pytest.skip("No cliente_id from previous test")
        
        credito_data = {
            "monto_original": 1000000,  # 1 million Gs
            "descripcion": "TEST_Credito manual de prueba"
        }
        
        response = requests.post(f"{BASE_URL}/api/clientes/{cliente_id}/creditos", json=credito_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create credito: {response.text}"
        
        data = response.json()
        # Handle string or number response
        monto_original = float(data["monto_original"]) if isinstance(data["monto_original"], str) else data["monto_original"]
        monto_pendiente = float(data["monto_pendiente"]) if isinstance(data["monto_pendiente"], str) else data["monto_pendiente"]
        
        assert monto_original == 1000000, f"monto_original incorrect: {data['monto_original']}"
        assert monto_pendiente == 1000000, f"monto_pendiente incorrect: {data['monto_pendiente']}"
        assert "id" in data, "credito id not returned"
        
        self.__class__.credito_id = data["id"]
        print(f"Created credito with id={data['id']}, monto={data['monto_original']}")
    
    def test_05_list_creditos_pendientes(self):
        """Test 3b: List pending credits for cliente"""
        cliente_id = getattr(self.__class__, 'cliente_id', None)
        if not cliente_id:
            pytest.skip("No cliente_id from previous test")
        
        response = requests.get(f"{BASE_URL}/api/clientes/{cliente_id}/creditos?solo_pendientes=true", headers=self.headers)
        assert response.status_code == 200, f"Failed to list creditos: {response.text}"
        
        creditos = response.json()
        assert len(creditos) >= 1, "No pending credits found"
        
        test_credito = next((c for c in creditos if "TEST_Credito" in (c.get("descripcion") or "")), None)
        assert test_credito is not None, "Test credito not found"
        assert test_credito["pagado"] == False
        print(f"Found {len(creditos)} pending credits")
    
    def test_06_pago_parcial_credito(self):
        """Test 4: Partial payment of credit"""
        credito_id = getattr(self.__class__, 'credito_id', None)
        if not credito_id:
            pytest.skip("No credito_id from previous test")
        
        # Pay 500,000 of 1,000,000
        pago_data = {
            "monto": 500000,
            "observacion": "TEST_Pago parcial"
        }
        
        response = requests.post(f"{BASE_URL}/api/creditos/{credito_id}/pagar", json=pago_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to pay credito: {response.text}"
        
        data = response.json()
        assert data["monto_pagado"] == 500000
        assert data["monto_pendiente"] == 500000  # 1M - 500K = 500K
        assert data["pagado"] == False  # Still not fully paid
        print(f"Partial payment: paid={data['monto_pagado']}, pending={data['monto_pendiente']}")
    
    def test_07_pago_completo_credito(self):
        """Test 4b: Complete payment of remaining credit"""
        credito_id = getattr(self.__class__, 'credito_id', None)
        if not credito_id:
            pytest.skip("No credito_id from previous test")
        
        # Pay remaining 500,000
        pago_data = {
            "monto": 500000,
            "observacion": "TEST_Pago final"
        }
        
        response = requests.post(f"{BASE_URL}/api/creditos/{credito_id}/pagar", json=pago_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to complete payment: {response.text}"
        
        data = response.json()
        assert data["monto_pendiente"] == 0
        assert data["pagado"] == True  # Now fully paid
        print(f"Credit fully paid: pending={data['monto_pendiente']}, pagado={data['pagado']}")


class TestVentasCredito:
    """Tests for credit sales validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token and create test data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.usuario_id = response.json()["usuario"]["id"]
    
    def test_08_create_cliente_for_venta(self):
        """Create cliente with limited credit for venta tests"""
        cliente_data = {
            "empresa_id": EMPRESA_ID,
            "nombre": "TEST_Cliente_Venta_Credito",
            "apellido": "Limite",
            "ruc": "TEST789012-3",
            "limite_credito": 2000000  # 2 million limit
        }
        
        response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=self.headers)
        assert response.status_code == 200
        self.__class__.venta_cliente_id = response.json()["id"]
        print(f"Created cliente for venta tests: id={self.__class__.venta_cliente_id}")
    
    def test_09_create_producto_for_venta(self):
        """Create producto for venta tests"""
        # First create almacen
        almacen_data = {"empresa_id": EMPRESA_ID, "nombre": "TEST_Almacen_Credito"}
        response = requests.post(f"{BASE_URL}/api/almacenes", json=almacen_data, headers=self.headers)
        if response.status_code == 200:
            self.__class__.almacen_id = response.json()["id"]
        else:
            # Get existing almacen
            response = requests.get(f"{BASE_URL}/api/almacenes?empresa_id={EMPRESA_ID}", headers=self.headers)
            almacenes = response.json()
            self.__class__.almacen_id = almacenes[0]["id"] if almacenes else None
        
        # Create producto
        producto_data = {
            "empresa_id": EMPRESA_ID,
            "nombre": "TEST_Producto_Credito",
            "codigo_barra": f"TEST{datetime.now().timestamp()}",
            "precio_venta": 500000
        }
        response = requests.post(f"{BASE_URL}/api/productos", json=producto_data, headers=self.headers)
        assert response.status_code == 200
        self.__class__.producto_id = response.json()["id"]
        
        # Add stock
        if self.__class__.almacen_id:
            stock_data = {
                "producto_id": self.__class__.producto_id,
                "almacen_id": self.__class__.almacen_id,
                "cantidad": 100
            }
            requests.post(f"{BASE_URL}/api/stock", json=stock_data, headers=self.headers)
        
        print(f"Created producto: id={self.__class__.producto_id}")
    
    def test_10_venta_credito_validates_limit(self):
        """Test 5: Venta a crédito validates credit limit"""
        cliente_id = getattr(self.__class__, 'venta_cliente_id', None)
        producto_id = getattr(self.__class__, 'producto_id', None)
        
        if not cliente_id or not producto_id:
            pytest.skip("Missing test data from previous tests")
        
        # Try to create venta exceeding credit limit (2M limit, trying 5M)
        venta_data = {
            "empresa_id": EMPRESA_ID,
            "cliente_id": cliente_id,
            "usuario_id": self.usuario_id,
            "tipo_pago": "CREDITO",
            "items": [
                {
                    "producto_id": producto_id,
                    "cantidad": 10,  # 10 x 500K = 5M > 2M limit
                    "precio_unitario": 500000
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data, headers=self.headers)
        # Should fail because 5M > 2M limit
        assert response.status_code == 400, f"Should have rejected venta exceeding limit: {response.text}"
        assert "Crédito insuficiente" in response.text or "crédito" in response.text.lower()
        print(f"Correctly rejected venta exceeding credit limit: {response.json()}")
    
    def test_11_venta_credito_within_limit(self):
        """Test 5b: Venta a crédito within limit succeeds"""
        cliente_id = getattr(self.__class__, 'venta_cliente_id', None)
        producto_id = getattr(self.__class__, 'producto_id', None)
        
        if not cliente_id or not producto_id:
            pytest.skip("Missing test data from previous tests")
        
        # Create venta within limit (2 x 500K = 1M < 2M limit)
        venta_data = {
            "empresa_id": EMPRESA_ID,
            "cliente_id": cliente_id,
            "usuario_id": self.usuario_id,
            "tipo_pago": "CREDITO",
            "items": [
                {
                    "producto_id": producto_id,
                    "cantidad": 2,  # 2 x 500K = 1M < 2M limit
                    "precio_unitario": 500000
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create venta: {response.text}"
        
        self.__class__.venta_id = response.json()["id"]
        print(f"Created venta within limit: id={self.__class__.venta_id}")
    
    def test_12_confirmar_venta_creates_credito(self):
        """Test 6: Confirming credit sale creates credit record"""
        venta_id = getattr(self.__class__, 'venta_id', None)
        cliente_id = getattr(self.__class__, 'venta_cliente_id', None)
        
        if not venta_id:
            pytest.skip("No venta_id from previous test")
        
        # Confirm the venta
        response = requests.post(f"{BASE_URL}/api/ventas/{venta_id}/confirmar", headers=self.headers)
        assert response.status_code == 200, f"Failed to confirm venta: {response.text}"
        
        # Check that credit record was created
        response = requests.get(f"{BASE_URL}/api/clientes/{cliente_id}/creditos", headers=self.headers)
        assert response.status_code == 200
        
        creditos = response.json()
        venta_credito = next((c for c in creditos if c.get("venta_id") == venta_id), None)
        assert venta_credito is not None, "Credit record not created for confirmed venta"
        assert venta_credito["pagado"] == False
        print(f"Credit record created for venta: credito_id={venta_credito['id']}, monto={venta_credito['monto_original']}")


class TestReportesPDF:
    """Tests for PDF report generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_13_reporte_ventas_pdf(self):
        """Test 7a: Download ventas report PDF"""
        today = date.today()
        fecha_desde = today.replace(day=1).isoformat()
        fecha_hasta = today.isoformat()
        
        response = requests.get(
            f"{BASE_URL}/api/reportes/ventas?empresa_id={EMPRESA_ID}&fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get ventas report: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        assert len(response.content) > 0
        print(f"Ventas report PDF downloaded: {len(response.content)} bytes")
    
    def test_14_reporte_stock_pdf(self):
        """Test 8: Download stock report PDF"""
        response = requests.get(
            f"{BASE_URL}/api/reportes/stock?empresa_id={EMPRESA_ID}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get stock report: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        assert len(response.content) > 0
        print(f"Stock report PDF downloaded: {len(response.content)} bytes")
    
    def test_15_reporte_deudas_proveedores_pdf(self):
        """Test 7b: Download deudas proveedores report PDF"""
        response = requests.get(
            f"{BASE_URL}/api/reportes/deudas-proveedores?empresa_id={EMPRESA_ID}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get deudas report: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        assert len(response.content) > 0
        print(f"Deudas proveedores report PDF downloaded: {len(response.content)} bytes")
    
    def test_16_reporte_creditos_clientes_pdf(self):
        """Test 7c: Download creditos clientes report PDF"""
        response = requests.get(
            f"{BASE_URL}/api/reportes/creditos-clientes?empresa_id={EMPRESA_ID}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get creditos report: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        assert len(response.content) > 0
        print(f"Creditos clientes report PDF downloaded: {len(response.content)} bytes")


class TestCiclosSalario:
    """Tests for salary cycle generation and alerts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_17_create_funcionario_for_ciclo(self):
        """Create funcionario for ciclo tests"""
        funcionario_data = {
            "empresa_id": EMPRESA_ID,
            "nombre": "TEST_Funcionario_Ciclo",
            "apellido": "Salario",
            "cedula": "TEST123456",
            "cargo": "Vendedor",
            "salario_base": 3000000  # 3 million Gs
        }
        
        response = requests.post(f"{BASE_URL}/api/funcionarios", json=funcionario_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to create funcionario: {response.text}"
        self.__class__.funcionario_id = response.json()["id"]
        print(f"Created funcionario: id={self.__class__.funcionario_id}")
    
    def test_18_generar_ciclo_salario(self):
        """Test 9: Generate salary cycles for funcionarios"""
        # Use a test month that won't conflict
        test_mes = "2025-12"  # December 2025
        
        response = requests.post(
            f"{BASE_URL}/api/ciclos-salario/generar?empresa_id={EMPRESA_ID}&mes={test_mes}",
            headers=self.headers
        )
        
        # May fail if cycles already exist for this month
        if response.status_code == 400 and "Ya existen ciclos" in response.text:
            print(f"Cycles already exist for {test_mes}, skipping creation")
            return
        
        assert response.status_code == 200, f"Failed to generate ciclos: {response.text}"
        
        data = response.json()
        assert "ciclos_creados" in data
        assert data["ciclos_creados"] >= 1
        print(f"Generated {data['ciclos_creados']} salary cycles for {test_mes}")
    
    def test_19_list_ciclos_salario(self):
        """Test 9b: List salary cycles"""
        response = requests.get(
            f"{BASE_URL}/api/ciclos-salario?empresa_id={EMPRESA_ID}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to list ciclos: {response.text}"
        
        ciclos = response.json()
        assert isinstance(ciclos, list)
        print(f"Found {len(ciclos)} salary cycles")
    
    def test_20_alertas_salarios_pendientes(self):
        """Test 10: Get pending salary alerts"""
        response = requests.get(
            f"{BASE_URL}/api/ciclos-salario/alertas?empresa_id={EMPRESA_ID}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get alertas: {response.text}"
        
        alertas = response.json()
        assert isinstance(alertas, list)
        
        # Check alert structure if any exist
        if alertas:
            alerta = alertas[0]
            assert "tipo" in alerta
            assert "mensaje" in alerta
            assert "monto" in alerta
            assert alerta["tipo"] == "salario_pendiente"
        
        print(f"Found {len(alertas)} pending salary alerts")


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_99_cleanup_test_data(self):
        """Cleanup TEST_ prefixed data"""
        # Get and delete test clientes
        response = requests.get(f"{BASE_URL}/api/clientes?empresa_id={EMPRESA_ID}", headers=self.headers)
        if response.status_code == 200:
            for cliente in response.json():
                if cliente["nombre"].startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/clientes/{cliente['id']}", headers=self.headers)
        
        # Get and delete test funcionarios
        response = requests.get(f"{BASE_URL}/api/funcionarios?empresa_id={EMPRESA_ID}", headers=self.headers)
        if response.status_code == 200:
            for func in response.json():
                if func["nombre"].startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/funcionarios/{func['id']}", headers=self.headers)
        
        # Get and delete test productos
        response = requests.get(f"{BASE_URL}/api/productos?empresa_id={EMPRESA_ID}", headers=self.headers)
        if response.status_code == 200:
            for prod in response.json():
                if prod["nombre"].startswith("TEST_"):
                    requests.delete(f"{BASE_URL}/api/productos/{prod['id']}", headers=self.headers)
        
        print("Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
