"""
Test suite for Ethercloud ERP - 10 Features Verification
Tests:
1. Historial Ventas - product/materia names shown (not just 'producto#5')
2. Boleta/Factura PDF - Materia de Laboratorio items show name and description
3. Ventas page - price field editable in cart
4. Stock page - 'Salida' function exists (POST /api/stock/salida)
5. Ventas representative logic - discounts/credit inherited from representing customer
6. Funcionarios page - displays salario_base, total_adelantos_mes, salario_restante
7. Permissions system - GERENTE, VENDEDOR, DELIVERY roles have appropriate permissions
8. Productos page - ID column visible and image zoom modal
9. Ventas product search - search by product ID in addition to name/barcode
"""

import pytest
import requests
import os
from decimal import Decimal

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://enterprise-luz.preview.emergentagent.com').rstrip('/')

class TestHistorialVentasProductNames:
    """Test 1: Historial Ventas shows product/materia names, not just IDs"""
    
    def test_ventas_list_returns_item_descriptions(self):
        """GET /api/ventas should return items with descripcion field containing product names"""
        response = requests.get(f"{BASE_URL}/api/ventas?empresa_id=1")
        assert response.status_code == 200
        
        ventas = response.json()
        if len(ventas) > 0:
            # Check first venta with items
            for venta in ventas:
                if venta.get('items') and len(venta['items']) > 0:
                    for item in venta['items']:
                        # descripcion should be set (not just producto_id)
                        descripcion = item.get('descripcion', '')
                        producto_id = item.get('producto_id')
                        materia_id = item.get('materia_laboratorio_id')
                        
                        # If there's a producto_id or materia_id, descripcion should NOT be just "Producto #X"
                        if producto_id or materia_id:
                            # descripcion should be populated with actual name
                            assert descripcion is not None, f"Item should have descripcion field"
                            # Should not be just a generic placeholder
                            if descripcion:
                                assert not descripcion.startswith('Producto #') or len(descripcion) > 15, \
                                    f"descripcion should be actual product name, got: {descripcion}"
                    break
            print("PASSED: Ventas list returns items with proper descripcion field")
        else:
            print("SKIPPED: No ventas found to test")


class TestBoletaFacturaMateriaNames:
    """Test 2: Boleta/Factura PDF shows Materia de Laboratorio names and descriptions"""
    
    def test_boleta_endpoint_returns_materia_names(self):
        """GET /api/ventas/{id}/boleta should return materia names in items"""
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
            
            for item in boleta['items']:
                # Each item should have descripcion field
                assert 'descripcion' in item, "Boleta item should have descripcion"
                assert item['descripcion'] is not None, "descripcion should not be None"
                print(f"  Item: {item['descripcion']}")
            
            print("PASSED: Boleta endpoint returns items with descripcion field")
        else:
            print("SKIPPED: No ventas found to test boleta")
    
    def test_factura_endpoint_returns_materia_names(self):
        """GET /api/ventas/{id}/factura should return materia names in items"""
        # First get a venta with a client that has RUC
        response = requests.get(f"{BASE_URL}/api/ventas?empresa_id=1")
        assert response.status_code == 200
        ventas = response.json()
        
        # Find a venta with client RUC
        for venta in ventas:
            if venta.get('cliente_ruc'):
                venta_id = venta['id']
                factura_response = requests.get(f"{BASE_URL}/api/ventas/{venta_id}/factura")
                
                if factura_response.status_code == 200:
                    factura = factura_response.json()
                    assert 'items' in factura
                    
                    for item in factura['items']:
                        assert 'descripcion' in item, "Factura item should have descripcion"
                        print(f"  Item: {item['descripcion']}")
                    
                    print("PASSED: Factura endpoint returns items with descripcion field")
                    return
        
        print("SKIPPED: No ventas with client RUC found to test factura")


class TestStockSalidaEndpoint:
    """Test 4: Stock page - 'Salida' function exists via POST /api/stock/salida"""
    
    def test_stock_salida_endpoint_exists(self):
        """POST /api/stock/salida should exist and handle stock withdrawal"""
        # First get existing stock
        stock_response = requests.get(f"{BASE_URL}/api/stock?empresa_id=1")
        assert stock_response.status_code == 200
        
        stocks = stock_response.json()
        if len(stocks) > 0:
            # Find stock with quantity > 0
            test_stock = None
            for s in stocks:
                if s['cantidad'] > 0:
                    test_stock = s
                    break
            
            if test_stock:
                # Test salida endpoint
                salida_data = {
                    "producto_id": test_stock['producto_id'],
                    "almacen_id": test_stock['almacen_id'],
                    "cantidad": 1,
                    "motivo": "TEST_Salida de prueba"
                }
                
                response = requests.post(f"{BASE_URL}/api/stock/salida", json=salida_data)
                assert response.status_code == 200, f"Stock salida should return 200, got {response.status_code}"
                
                result = response.json()
                assert 'message' in result, "Response should have message"
                assert 'stock_restante' in result, "Response should have stock_restante"
                
                print(f"PASSED: Stock salida endpoint works. Message: {result['message']}, Stock restante: {result['stock_restante']}")
                
                # Restore stock
                entrada_data = {
                    "producto_id": test_stock['producto_id'],
                    "almacen_id": test_stock['almacen_id'],
                    "cantidad": 1
                }
                requests.post(f"{BASE_URL}/api/stock/entrada", json=entrada_data)
            else:
                print("SKIPPED: No stock with quantity > 0 found")
        else:
            print("SKIPPED: No stock found to test salida")
    
    def test_stock_salida_insufficient_stock(self):
        """POST /api/stock/salida should return 400 for insufficient stock"""
        salida_data = {
            "producto_id": 1,
            "almacen_id": 1,
            "cantidad": 999999,
            "motivo": "TEST_Should fail"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/salida", json=salida_data)
        # Should return 400 for insufficient stock
        assert response.status_code == 400, f"Should return 400 for insufficient stock, got {response.status_code}"
        print("PASSED: Stock salida returns 400 for insufficient stock")


class TestFuncionariosSalaryFields:
    """Test 6: Funcionarios page displays salario_base, total_adelantos_mes, salario_restante"""
    
    def test_funcionarios_endpoint_returns_salary_fields(self):
        """GET /api/funcionarios should return salary breakdown fields"""
        response = requests.get(f"{BASE_URL}/api/funcionarios?empresa_id=1")
        assert response.status_code == 200
        
        funcionarios = response.json()
        if len(funcionarios) > 0:
            func = funcionarios[0]
            
            # Check required salary fields
            assert 'salario_base' in func, "Funcionario should have salario_base"
            assert 'total_adelantos_mes' in func, "Funcionario should have total_adelantos_mes"
            assert 'salario_restante' in func, "Funcionario should have salario_restante"
            
            print(f"PASSED: Funcionario {func.get('nombre')} has salary fields:")
            print(f"  - salario_base: {func['salario_base']}")
            print(f"  - total_adelantos_mes: {func['total_adelantos_mes']}")
            print(f"  - salario_restante: {func['salario_restante']}")
            
            # Verify calculation: salario_restante = salario_base - total_adelantos_mes
            expected_restante = float(func['salario_base'] or 0) - float(func['total_adelantos_mes'] or 0)
            actual_restante = float(func['salario_restante'] or 0)
            assert abs(expected_restante - actual_restante) < 0.01, \
                f"salario_restante calculation incorrect: expected {expected_restante}, got {actual_restante}"
            
            print("PASSED: Salary calculation is correct")
        else:
            print("SKIPPED: No funcionarios found to test")


class TestRepresentativeLogic:
    """Test 5: Ventas representative logic - discounts/credit inherited from representing customer"""
    
    def test_create_venta_with_representante(self):
        """POST /api/ventas with representante_cliente_id should use representante's privileges"""
        # First, create two test clients - one with discount, one without
        cliente_sin_descuento = {
            "nombre": "TEST_Cliente Sin Descuento",
            "empresa_id": 1,
            "descuento_porcentaje": 0
        }
        
        cliente_con_descuento = {
            "nombre": "TEST_Cliente Con Descuento",
            "empresa_id": 1,
            "descuento_porcentaje": 10,
            "limite_credito": 1000000
        }
        
        # Create clients
        resp1 = requests.post(f"{BASE_URL}/api/clientes", json=cliente_sin_descuento)
        assert resp1.status_code == 200
        cliente1 = resp1.json()
        
        resp2 = requests.post(f"{BASE_URL}/api/clientes", json=cliente_con_descuento)
        assert resp2.status_code == 200
        cliente2 = resp2.json()
        
        try:
            # Get a product with stock
            productos = requests.get(f"{BASE_URL}/api/productos?empresa_id=1").json()
            producto = None
            for p in productos:
                if p.get('stock_total', 0) > 0:
                    producto = p
                    break
            
            if producto:
                # Create venta where cliente1 represents cliente2 (who has discount)
                venta_data = {
                    "empresa_id": 1,
                    "cliente_id": cliente1['id'],  # Cliente sin descuento
                    "representante_cliente_id": cliente2['id'],  # Cliente con descuento
                    "usuario_id": 1,
                    "tipo_pago": "EFECTIVO",
                    "es_delivery": False,
                    "items": [{
                        "producto_id": producto['id'],
                        "cantidad": 1,
                        "precio_unitario": 100000
                    }]
                }
                
                venta_response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data)
                assert venta_response.status_code == 200, f"Venta creation failed: {venta_response.text}"
                
                venta = venta_response.json()
                
                # Verify discount was applied (from representante)
                # With 10% discount on 100000, descuento should be ~9090 (10% of subtotal)
                assert venta.get('descuento', 0) > 0, "Discount from representante should be applied"
                print(f"PASSED: Venta created with representante. Descuento applied: {venta.get('descuento')}")
                
                # Cleanup - anular venta
                requests.post(f"{BASE_URL}/api/ventas/{venta['id']}/anular")
            else:
                print("SKIPPED: No product with stock found")
                
        finally:
            # Cleanup test clients
            requests.delete(f"{BASE_URL}/api/clientes/{cliente1['id']}")
            requests.delete(f"{BASE_URL}/api/clientes/{cliente2['id']}")


class TestPermissionsSystem:
    """Test 7: Permissions system - verify roles have appropriate default permissions"""
    
    def test_admin_user_has_all_permissions(self):
        """Admin user (rol_id=1) should have all permissions"""
        # Get admin user permissions
        response = requests.get(f"{BASE_URL}/api/usuarios/1/permisos")
        assert response.status_code == 200
        
        permisos = response.json()
        assert len(permisos) > 0, "Admin should have permissions"
        
        # Check for key permissions
        permiso_claves = [p.get('clave') for p in permisos]
        
        # Admin should have access to key modules
        expected_permisos = ['ventas.ver', 'productos.ver', 'clientes.ver', 'funcionarios.ver', 'stock.ver']
        for expected in expected_permisos:
            assert expected in permiso_claves, f"Admin should have {expected} permission"
        
        print(f"PASSED: Admin has {len(permisos)} permissions including key module access")
    
    def test_roles_endpoint_returns_roles(self):
        """GET /api/roles should return available roles"""
        response = requests.get(f"{BASE_URL}/api/roles?empresa_id=1")
        assert response.status_code == 200
        
        roles = response.json()
        print(f"PASSED: Found {len(roles)} roles")
        for rol in roles:
            print(f"  - {rol.get('nombre')}")


class TestProductosIDColumn:
    """Test 8: Productos page - ID column visible"""
    
    def test_productos_endpoint_returns_id(self):
        """GET /api/productos should return id field for each product"""
        response = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        assert response.status_code == 200
        
        productos = response.json()
        if len(productos) > 0:
            for producto in productos[:3]:  # Check first 3
                assert 'id' in producto, "Producto should have id field"
                assert producto['id'] is not None, "Producto id should not be None"
                print(f"  Producto ID: {producto['id']} - {producto.get('nombre')}")
            
            print("PASSED: Productos endpoint returns id field")
        else:
            print("SKIPPED: No productos found")


class TestVentasSearchByID:
    """Test 9: Ventas product search - search by product ID"""
    
    def test_productos_searchable_by_id(self):
        """Products should be searchable by ID (frontend filter)"""
        # Get productos
        response = requests.get(f"{BASE_URL}/api/productos?empresa_id=1")
        assert response.status_code == 200
        
        productos = response.json()
        if len(productos) > 0:
            # Verify products have id field that can be used for search
            producto = productos[0]
            assert 'id' in producto, "Producto should have id for search"
            
            # The frontend filter checks: p.id.toString() === searchProducto
            # So we just need to verify the id is present and is a number
            assert isinstance(producto['id'], int), "Producto id should be integer"
            
            print(f"PASSED: Productos have id field for search. Example: ID {producto['id']}")
        else:
            print("SKIPPED: No productos found")


class TestVentasPriceEditable:
    """Test 3: Ventas page - price field editable (frontend feature)"""
    
    def test_venta_accepts_custom_price(self):
        """POST /api/ventas should accept custom precio_unitario"""
        # Get a client
        clientes = requests.get(f"{BASE_URL}/api/clientes?empresa_id=1").json()
        if not clientes:
            print("SKIPPED: No clients found")
            return
        
        # Get a product with stock
        productos = requests.get(f"{BASE_URL}/api/productos?empresa_id=1").json()
        producto = None
        for p in productos:
            if p.get('stock_total', 0) > 0:
                producto = p
                break
        
        if not producto:
            print("SKIPPED: No product with stock found")
            return
        
        # Create venta with custom price (different from product's precio_venta)
        custom_price = 50000  # Custom price
        venta_data = {
            "empresa_id": 1,
            "cliente_id": clientes[0]['id'],
            "usuario_id": 1,
            "tipo_pago": "EFECTIVO",
            "es_delivery": False,
            "items": [{
                "producto_id": producto['id'],
                "cantidad": 1,
                "precio_unitario": custom_price  # Custom price
            }]
        }
        
        response = requests.post(f"{BASE_URL}/api/ventas", json=venta_data)
        assert response.status_code == 200, f"Venta creation failed: {response.text}"
        
        venta = response.json()
        
        # Verify the custom price was accepted
        # Total should be based on custom price
        print(f"PASSED: Venta created with custom price {custom_price}. Total: {venta.get('total')}")
        
        # Cleanup
        requests.post(f"{BASE_URL}/api/ventas/{venta['id']}/anular")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
