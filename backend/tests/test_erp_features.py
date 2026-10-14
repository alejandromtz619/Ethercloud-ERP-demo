"""
Ethercloud ERP - Backend API Tests
Tests for: Login, Delivery, Ventas (cheque validation), Funcionarios (adelantos), 
Proveedores (deudas), Cotización, Marcas, Permisos
"""
import pytest
import requests
import os
from datetime import date, datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://enterprise-luz.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "admin@ether.com"
TEST_PASSWORD = "admin123"
EMPRESA_ID = 1


class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    def test_health_endpoint(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_login_with_valid_credentials(self):
        """Test login with admin@ether.com / admin123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "usuario" in data
        assert data["usuario"]["email"] == TEST_EMAIL
        print(f"✓ Login successful for {TEST_EMAIL}")
        return data["access_token"]
    
    def test_login_with_invalid_credentials(self):
        """Test login with wrong credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")


class TestDeliveryPage:
    """Tests for Delivery module - entregas endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_entregas(self, auth_token):
        """Test listing entregas - Delivery page loads without error"""
        response = requests.get(
            f"{BASE_URL}/api/entregas?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Entregas endpoint works, returned {len(data)} items")
    
    def test_list_vehiculos(self, auth_token):
        """Test listing vehiculos for delivery"""
        response = requests.get(
            f"{BASE_URL}/api/vehiculos?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Vehiculos endpoint works, returned {len(data)} items")


class TestVentasChequeValidation:
    """Tests for Ventas module - cheque payment validation"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_clientes(self, auth_token):
        """Test listing clientes"""
        response = requests.get(
            f"{BASE_URL}/api/clientes?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Clientes endpoint works, returned {len(data)} items")
        return data
    
    def test_create_cliente_without_cheque(self, auth_token):
        """Create a test client without cheque permission"""
        response = requests.post(
            f"{BASE_URL}/api/clientes",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Cliente_Sin_Cheque",
                "apellido": "Test",
                "empresa_id": EMPRESA_ID,
                "acepta_cheque": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["acepta_cheque"] == False
        print(f"✓ Created client without cheque permission: {data['nombre']}")
        return data
    
    def test_create_cliente_with_cheque(self, auth_token):
        """Create a test client with cheque permission"""
        response = requests.post(
            f"{BASE_URL}/api/clientes",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Cliente_Con_Cheque",
                "apellido": "Test",
                "empresa_id": EMPRESA_ID,
                "acepta_cheque": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["acepta_cheque"] == True
        print(f"✓ Created client with cheque permission: {data['nombre']}")
        return data
    
    def test_venta_cheque_validation_rejected(self, auth_token):
        """Test that cheque payment is rejected for client without acepta_cheque"""
        # First create a client without cheque permission
        client_response = requests.post(
            f"{BASE_URL}/api/clientes",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Cheque_Validation",
                "apellido": "Test",
                "empresa_id": EMPRESA_ID,
                "acepta_cheque": False
            }
        )
        client = client_response.json()
        
        # Get user ID
        user_response = requests.get(
            f"{BASE_URL}/api/usuarios?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        users = user_response.json()
        user_id = users[0]["id"] if users else 1
        
        # Try to create a sale with cheque payment
        venta_response = requests.post(
            f"{BASE_URL}/api/ventas",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "empresa_id": EMPRESA_ID,
                "cliente_id": client["id"],
                "usuario_id": user_id,
                "tipo_pago": "CHEQUE",
                "es_delivery": False,
                "items": [
                    {
                        "producto_id": None,
                        "materia_laboratorio_id": None,
                        "cantidad": 1,
                        "precio_unitario": 10000,
                        "observaciones": "Test item"
                    }
                ]
            }
        )
        
        # Should be rejected with 400 error
        assert venta_response.status_code == 400, f"Expected 400, got {venta_response.status_code}: {venta_response.text}"
        error_data = venta_response.json()
        assert "cheque" in error_data.get("detail", "").lower()
        print(f"✓ Cheque payment correctly rejected for client without acepta_cheque")


class TestFuncionariosAdelantos:
    """Tests for Funcionarios module - salary advances"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_funcionarios(self, auth_token):
        """Test listing funcionarios"""
        response = requests.get(
            f"{BASE_URL}/api/funcionarios?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Funcionarios endpoint works, returned {len(data)} items")
        return data
    
    def test_create_funcionario(self, auth_token):
        """Test creating a funcionario"""
        response = requests.post(
            f"{BASE_URL}/api/funcionarios",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Funcionario",
                "apellido": "Adelanto",
                "cedula": "1234567",
                "cargo": "Vendedor",
                "salario_base": 2500000,
                "empresa_id": EMPRESA_ID
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "TEST_Funcionario"
        assert float(data["salario_base"]) == 2500000
        print(f"✓ Created funcionario: {data['nombre']}")
        return data
    
    def test_create_adelanto_salario(self, auth_token):
        """Test creating salary advance for funcionario"""
        # First create a funcionario
        func_response = requests.post(
            f"{BASE_URL}/api/funcionarios",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Adelanto_Func",
                "apellido": "Test",
                "salario_base": 3000000,
                "empresa_id": EMPRESA_ID
            }
        )
        funcionario = func_response.json()
        
        # Create adelanto
        adelanto_response = requests.post(
            f"{BASE_URL}/api/funcionarios/{funcionario['id']}/adelantos",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"monto": 500000}
        )
        assert adelanto_response.status_code == 200, f"Failed: {adelanto_response.text}"
        adelanto = adelanto_response.json()
        assert float(adelanto["monto"]) == 500000
        print(f"✓ Created adelanto of 500000 for funcionario {funcionario['id']}")
        
        # Verify adelanto is listed
        list_response = requests.get(
            f"{BASE_URL}/api/funcionarios/{funcionario['id']}/adelantos",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert list_response.status_code == 200
        adelantos = list_response.json()
        assert len(adelantos) >= 1
        print(f"✓ Adelanto correctly listed, total adelantos: {len(adelantos)}")


class TestProveedoresDeudas:
    """Tests for Proveedores module - supplier debts with dates"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_proveedores(self, auth_token):
        """Test listing proveedores"""
        response = requests.get(
            f"{BASE_URL}/api/proveedores?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Proveedores endpoint works, returned {len(data)} items")
        return data
    
    def test_create_proveedor(self, auth_token):
        """Test creating a proveedor"""
        response = requests.post(
            f"{BASE_URL}/api/proveedores",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Proveedor_Deuda",
                "ruc": "80000000-1",
                "direccion": "Asunción",
                "telefono": "021-123456",
                "empresa_id": EMPRESA_ID
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "TEST_Proveedor_Deuda"
        print(f"✓ Created proveedor: {data['nombre']}")
        return data
    
    def test_create_deuda_with_fecha_limite(self, auth_token):
        """Test creating supplier debt with fecha_limite"""
        # First create a proveedor
        prov_response = requests.post(
            f"{BASE_URL}/api/proveedores",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Proveedor_Fecha",
                "empresa_id": EMPRESA_ID
            }
        )
        proveedor = prov_response.json()
        
        # Create deuda with fecha_limite
        fecha_limite = "2026-02-28"
        deuda_response = requests.post(
            f"{BASE_URL}/api/proveedores/{proveedor['id']}/deudas",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "monto": 1500000,
                "descripcion": "Compra de mercadería",
                "fecha_limite": fecha_limite
            }
        )
        assert deuda_response.status_code == 200, f"Failed: {deuda_response.text}"
        deuda = deuda_response.json()
        assert float(deuda["monto"]) == 1500000
        assert deuda.get("fecha_limite") == fecha_limite
        print(f"✓ Created deuda with fecha_limite: {fecha_limite}")
        
        # Verify deuda is listed
        list_response = requests.get(
            f"{BASE_URL}/api/proveedores/{proveedor['id']}/deudas",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert list_response.status_code == 200
        deudas = list_response.json()
        assert len(deudas) >= 1
        print(f"✓ Deuda correctly listed with fecha_limite")
    
    def test_pagar_deuda(self, auth_token):
        """Test marking a debt as paid"""
        # Create proveedor and deuda
        prov_response = requests.post(
            f"{BASE_URL}/api/proveedores",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"nombre": "TEST_Proveedor_Pago", "empresa_id": EMPRESA_ID}
        )
        proveedor = prov_response.json()
        
        deuda_response = requests.post(
            f"{BASE_URL}/api/proveedores/{proveedor['id']}/deudas",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"monto": 100000, "descripcion": "Test deuda"}
        )
        deuda = deuda_response.json()
        
        # Pay the debt
        pago_response = requests.put(
            f"{BASE_URL}/api/deudas/{deuda['id']}/pagar",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert pago_response.status_code == 200
        print(f"✓ Deuda marked as paid successfully")


class TestCotizacionDivisas:
    """Tests for currency exchange rates"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_cotizacion(self, auth_token):
        """Test getting currency exchange rates"""
        response = requests.get(
            f"{BASE_URL}/api/cotizacion",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "usd_pyg" in data
        assert "brl_pyg" in data
        assert "manual" in data
        print(f"✓ Cotización: USD/PYG={data['usd_pyg']}, BRL/PYG={data['brl_pyg']}, Manual={data['manual']}")
        return data
    
    def test_set_manual_cotizacion(self, auth_token):
        """Test setting manual exchange rates"""
        response = requests.post(
            f"{BASE_URL}/api/cotizacion/manual",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "usd_pyg": 7500,
                "brl_pyg": 1500,
                "manual": True
            }
        )
        assert response.status_code == 200
        print(f"✓ Manual cotización set: USD=7500, BRL=1500")
        
        # Verify it was set
        verify_response = requests.get(
            f"{BASE_URL}/api/cotizacion",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = verify_response.json()
        assert data["manual"] == True
        assert float(data["usd_pyg"]) == 7500
        print(f"✓ Manual cotización verified")
    
    def test_activate_auto_cotizacion(self, auth_token):
        """Test activating automatic exchange rates"""
        response = requests.post(
            f"{BASE_URL}/api/cotizacion/auto",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Automatic cotización activated")


class TestMarcasCRUD:
    """Tests for Marcas module - brands CRUD"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_marcas(self, auth_token):
        """Test listing marcas"""
        response = requests.get(
            f"{BASE_URL}/api/marcas?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Marcas endpoint works, returned {len(data)} items")
        return data
    
    def test_create_marca(self, auth_token):
        """Test creating a marca"""
        response = requests.post(
            f"{BASE_URL}/api/marcas",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Marca_Nueva",
                "empresa_id": EMPRESA_ID
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "TEST_Marca_Nueva"
        print(f"✓ Created marca: {data['nombre']}")
        return data
    
    def test_update_marca(self, auth_token):
        """Test updating a marca"""
        # First create a marca
        create_response = requests.post(
            f"{BASE_URL}/api/marcas",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"nombre": "TEST_Marca_Update", "empresa_id": EMPRESA_ID}
        )
        marca = create_response.json()
        
        # Update it
        update_response = requests.put(
            f"{BASE_URL}/api/marcas/{marca['id']}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"nombre": "TEST_Marca_Updated"}
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["nombre"] == "TEST_Marca_Updated"
        print(f"✓ Updated marca: {updated['nombre']}")
    
    def test_delete_marca(self, auth_token):
        """Test deleting a marca"""
        # First create a marca
        create_response = requests.post(
            f"{BASE_URL}/api/marcas",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"nombre": "TEST_Marca_Delete", "empresa_id": EMPRESA_ID}
        )
        marca = create_response.json()
        
        # Delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/marcas/{marca['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert delete_response.status_code == 200
        print(f"✓ Deleted marca successfully")


class TestPermisosRoles:
    """Tests for Permisos module - roles and permissions management"""
    
    @pytest.fixture
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_roles(self, auth_token):
        """Test listing roles"""
        response = requests.get(
            f"{BASE_URL}/api/roles?empresa_id={EMPRESA_ID}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Roles endpoint works, returned {len(data)} items")
        return data
    
    def test_list_permisos(self, auth_token):
        """Test listing permisos"""
        response = requests.get(
            f"{BASE_URL}/api/permisos",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Permisos endpoint works, returned {len(data)} items")
        return data
    
    def test_create_rol(self, auth_token):
        """Test creating a rol"""
        response = requests.post(
            f"{BASE_URL}/api/roles",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nombre": "TEST_Rol_Vendedor",
                "descripcion": "Rol de prueba para vendedores",
                "empresa_id": EMPRESA_ID
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "TEST_Rol_Vendedor"
        print(f"✓ Created rol: {data['nombre']}")
        return data
    
    def test_create_permiso(self, auth_token):
        """Test creating a permiso"""
        import uuid
        unique_key = f"test.permiso_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/permisos",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "clave": unique_key,
                "descripcion": "Permiso de prueba"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["clave"] == unique_key
        print(f"✓ Created permiso: {data['clave']}")
        return data
    
    def test_assign_permiso_to_rol(self, auth_token):
        """Test assigning a permiso to a rol"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        
        # Create rol
        rol_response = requests.post(
            f"{BASE_URL}/api/roles",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"nombre": f"TEST_Rol_Permisos_{unique_id}", "empresa_id": EMPRESA_ID}
        )
        rol = rol_response.json()
        
        # Create permiso
        permiso_response = requests.post(
            f"{BASE_URL}/api/permisos",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"clave": f"test.assign_{unique_id}", "descripcion": "Test"}
        )
        permiso = permiso_response.json()
        
        # Assign permiso to rol
        assign_response = requests.post(
            f"{BASE_URL}/api/roles/{rol['id']}/permisos/{permiso['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert assign_response.status_code == 200
        print(f"✓ Assigned permiso {permiso['clave']} to rol {rol['nombre']}")
        
        # Verify assignment
        verify_response = requests.get(
            f"{BASE_URL}/api/roles/{rol['id']}/permisos",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert verify_response.status_code == 200
        permisos = verify_response.json()
        assert any(p["id"] == permiso["id"] for p in permisos)
        print(f"✓ Permiso assignment verified")
    
    def test_remove_permiso_from_rol(self, auth_token):
        """Test removing a permiso from a rol"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        
        # Create rol and permiso
        rol_response = requests.post(
            f"{BASE_URL}/api/roles",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"nombre": f"TEST_Rol_Remove_{unique_id}", "empresa_id": EMPRESA_ID}
        )
        rol = rol_response.json()
        
        permiso_response = requests.post(
            f"{BASE_URL}/api/permisos",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"clave": f"test.remove_{unique_id}", "descripcion": "Test"}
        )
        permiso = permiso_response.json()
        
        # Assign then remove
        requests.post(
            f"{BASE_URL}/api/roles/{rol['id']}/permisos/{permiso['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        remove_response = requests.delete(
            f"{BASE_URL}/api/roles/{rol['id']}/permisos/{permiso['id']}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert remove_response.status_code == 200
        print(f"✓ Removed permiso from rol successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
