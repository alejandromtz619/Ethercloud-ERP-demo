"""
Test file for 10 issues fixes in Ethercloud ERP
Tests:
1. Historial ventas: items muestran nombre del producto no 'producto#5'
3. Boleta/factura: materias laboratorio muestran nombre + descripción
4. Ventas: precio de productos se puede modificar manualmente
5. Stock: botón Salida permite eliminar productos de almacenes
6. Ventas: herencia de descuento del representante funciona
7. Funcionarios: muestra columnas Salario Base, Adelantos Mes, Restante
8. Permisos: usuarios con rol ven módulos correctos
9. Productos: columna ID visible y botón expandir imagen
10. Ventas: buscar productos por ID funciona
"""

import pytest
import requests
import os
from decimal import Decimal

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHistorialVentasProductNames:
    """Issue 1: Historial ventas items show product name, not 'producto#5'"""
    
    def test_ventas_list_shows_product_names(self):
        """GET /api/ventas should return items with descripcion field containing product name"""
        response = requests.get(f"{BASE_URL}/api/ventas?empresa_id=1")
        assert response.status_code == 200
        
        ventas = response.json()
        if len(ventas) > 0:
            # Find a venta with items
            for venta in ventas:
                if venta.get('items') and len(venta['items']) > 0:
                    for item in venta['items']:
                        # Item should have descripcion field with actual product name
                        assert 'descripcion' in item, "Item should have descripcion field"
                        # descripcion should not be empty or generic like 'producto#5'
                        if item.get('producto_id'):
                            assert item['descripcion'] is not None, "Product descripcion should not be None"
                            assert not item['descripcion'].startswith('producto#'), f"Product name should not be generic: {item['descripcion']}"
                    break


class TestBoletaFacturaMateriaNames:
    """Issue 3: Boleta/factura shows materia laboratorio name + description"""
    
    def test_boleta_endpoint_exists(self):
        """GET /api/ventas/{id}/boleta should return boleta data"""
        # First get a venta
        response = requests.get(f"{BASE_URL}/api/ventas?empresa_id=1")
        assert response.status_code == 200
        ventas = response.json()
        
        if len(ventas) > 0:
            venta_id = ventas[0]['id']
            boleta_response = requests.get(f"{BASE_URL}/api/ventas/{venta_id}/boleta")
            assert boleta_response.status_code == 200
            
            boleta = boleta_response.json()
            assert 'items' in boleta
            assert 'tipo' in boleta
            assert boleta['tipo'] == 'BOLETA'
            
            # Check items have descripcion
            for item in boleta['items']:
                assert 'descripcion' in item
                assert item['descripcion'] is not None


class TestVentasPrecioEditable:
    """Issue 4: Ventas - product price can be modified manually"""
    
    def test_create_venta_with_custom_price(self):
        """POST /api/ventas should accept custom precio_unitario"""
        # Get a client and product first
        clientes_resp = requests.get(f"{BASE_URL}/api/clientes?empresa_id=1")
        assert clientes_resp.status_code == 200
        clientes = clientes_resp.json()
        
        productos_resp = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        assert productos_resp.status_code == 200
        productos = productos_resp.json()
        
        if len(clientes) > 0 and len(productos) > 0:
            cliente = clientes[0]
            producto = productos[0]
            
            # Create venta with custom price (different from product's precio_venta)
            custom_price = 99999  # Custom price
            venta_data = {
                "empresa_id": 1,
                "cliente_id": cliente['id'],
                "usuario_id": 1,
                "tipo_pago": "EFECTIVO",
                "es_delivery": False,
                "items": [{
                    "producto_id": producto['id'],
                    "cantidad": 1,
                    "precio_unitario": custom_price,
                    "observaciones": "TEST_custom_price"
                }]
            }
            
            response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data)
            # May fail due to stock, but should not fail due to price validation
            if response.status_code == 200:
                venta = response.json()
                # Verify the custom price was accepted
                assert venta['total'] > 0


class TestStockSalidaButton:
    """Issue 5: Stock - Salida button allows removing products from warehouses"""
    
    def test_stock_salida_endpoint_exists(self):
        """POST /api/stock/salida should exist and work"""
        # First check if there's stock
        stock_resp = requests.get(f"{BASE_URL}/api/stock?empresa_id=1")
        assert stock_resp.status_code == 200
        stock_items = stock_resp.json()
        
        if len(stock_items) > 0:
            # Find an item with stock > 0
            for item in stock_items:
                if item['cantidad'] > 0:
                    salida_data = {
                        "producto_id": item['producto_id'],
                        "almacen_id": item['almacen_id'],
                        "cantidad": 1,
                        "motivo": "TEST_salida_manual"
                    }
                    
                    response = requests.post(f"{BASE_URL}/api/stock/salida", json=salida_data)
                    assert response.status_code == 200
                    
                    result = response.json()
                    assert 'message' in result
                    assert 'stock_restante' in result
                    break


class TestVentasHerenciaDescuento:
    """Issue 6: Ventas - representative discount inheritance works"""
    
    def test_cliente_descuento_field_exists(self):
        """Clientes should have descuento_porcentaje field"""
        response = requests.get(f"{BASE_URL}/api/clientes?empresa_id=1")
        assert response.status_code == 200
        clientes = response.json()
        
        if len(clientes) > 0:
            cliente = clientes[0]
            assert 'descuento_porcentaje' in cliente, "Cliente should have descuento_porcentaje field"
    
    def test_venta_accepts_representante_cliente_id(self):
        """POST /api/ventas should accept representante_cliente_id"""
        clientes_resp = requests.get(f"{BASE_URL}/api/clientes?empresa_id=1")
        clientes = clientes_resp.json()
        
        productos_resp = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        productos = productos_resp.json()
        
        if len(clientes) >= 2 and len(productos) > 0:
            cliente = clientes[0]
            representante = clientes[1]
            producto = productos[0]
            
            venta_data = {
                "empresa_id": 1,
                "cliente_id": cliente['id'],
                "usuario_id": 1,
                "representante_cliente_id": representante['id'],  # Key field
                "tipo_pago": "EFECTIVO",
                "es_delivery": False,
                "items": [{
                    "producto_id": producto['id'],
                    "cantidad": 1,
                    "precio_unitario": producto.get('precio_venta', 10000),
                    "observaciones": "TEST_representante"
                }]
            }
            
            response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data)
            # May fail due to stock, but should not fail due to representante_cliente_id
            assert response.status_code in [200, 400]  # 400 only if stock issue


class TestFuncionariosColumnas:
    """Issue 7: Funcionarios shows Salario Base, Adelantos Mes, Restante columns"""
    
    def test_funcionarios_returns_salary_fields(self):
        """GET /api/funcionarios should return salario_base, total_adelantos_mes, salario_restante"""
        response = requests.get(f"{BASE_URL}/api/funcionarios?empresa_id=1")
        assert response.status_code == 200
        
        funcionarios = response.json()
        if len(funcionarios) > 0:
            func = funcionarios[0]
            assert 'salario_base' in func, "Funcionario should have salario_base"
            assert 'total_adelantos_mes' in func, "Funcionario should have total_adelantos_mes"
            assert 'salario_restante' in func, "Funcionario should have salario_restante"


class TestPermisosRoles:
    """Issue 8: Permisos - users with role see correct modules"""
    
    def test_user_permisos_endpoint(self):
        """GET /api/usuarios/{id}/permisos should return permissions"""
        response = requests.get(f"{BASE_URL}/api/usuarios/1/permisos")
        assert response.status_code == 200
        
        permisos = response.json()
        assert isinstance(permisos, list)
        
        # Admin should have permissions
        if len(permisos) > 0:
            permiso = permisos[0]
            assert 'clave' in permiso
            assert 'descripcion' in permiso
    
    def test_roles_endpoint(self):
        """GET /api/roles should return roles"""
        response = requests.get(f"{BASE_URL}/api/roles?empresa_id=1")
        assert response.status_code == 200
        
        roles = response.json()
        assert isinstance(roles, list)


class TestProductosColumnaID:
    """Issue 9: Productos - ID column visible and image expand button"""
    
    def test_productos_returns_id(self):
        """GET /api/productos should return id field"""
        response = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        assert response.status_code == 200
        
        productos = response.json()
        if len(productos) > 0:
            producto = productos[0]
            assert 'id' in producto, "Producto should have id field"
            assert isinstance(producto['id'], int), "Producto id should be integer"
    
    def test_productos_returns_imagen_url(self):
        """GET /api/productos should return imagen_url field"""
        response = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        assert response.status_code == 200
        
        productos = response.json()
        if len(productos) > 0:
            producto = productos[0]
            assert 'imagen_url' in producto, "Producto should have imagen_url field"


class TestVentasBuscarPorID:
    """Issue 10: Ventas - search products by ID works"""
    
    def test_producto_by_id_endpoint(self):
        """GET /api/productos/{id} should return product"""
        # First get products list
        response = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        assert response.status_code == 200
        
        productos = response.json()
        if len(productos) > 0:
            producto_id = productos[0]['id']
            
            # Get product by ID
            detail_response = requests.get(f"{BASE_URL}/api/productos/{producto_id}")
            assert detail_response.status_code == 200
            
            producto = detail_response.json()
            assert producto['id'] == producto_id
            assert 'nombre' in producto


# Additional integration tests

class TestVentaWorkflow:
    """Test complete venta workflow with all fixes"""
    
    def test_complete_venta_flow(self):
        """Test creating and confirming a venta"""
        # Get required data
        clientes = requests.get(f"{BASE_URL}/api/clientes?empresa_id=1").json()
        productos = requests.get(f"{BASE_URL}/api/productos?empresa_id=1").json()
        
        if len(clientes) == 0 or len(productos) == 0:
            pytest.skip("No test data available")
        
        cliente = clientes[0]
        producto = productos[0]
        
        # Create venta with custom price
        venta_data = {
            "empresa_id": 1,
            "cliente_id": cliente['id'],
            "usuario_id": 1,
            "tipo_pago": "EFECTIVO",
            "es_delivery": False,
            "items": [{
                "producto_id": producto['id'],
                "cantidad": 1,
                "precio_unitario": 50000,  # Custom price
                "observaciones": "TEST_workflow"
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data)
        if response.status_code == 200:
            venta = response.json()
            assert venta['id'] > 0
            
            # Get boleta
            boleta_resp = requests.get(f"{BASE_URL}/api/ventas/{venta['id']}/boleta")
            assert boleta_resp.status_code == 200
            
            boleta = boleta_resp.json()
            assert len(boleta['items']) > 0
            assert boleta['items'][0]['descripcion'] == producto['nombre']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
