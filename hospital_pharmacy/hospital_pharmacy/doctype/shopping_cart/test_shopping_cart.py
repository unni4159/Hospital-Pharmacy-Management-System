# Copyright (c) 2026, UK and Contributors
# See license.txt

# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.tests.utils import FrappeTestCase
# pyrefly: ignore [missing-import]
from frappe.utils import today
from hospital_pharmacy.api import (
    ensure_custom_fields,
    get_customer,
    get_active_quotation,
    sync_quotation_to_shopping_cart,
    sync_quotation_from_shopping_cart
)

class TestShoppingCart(FrappeTestCase):
    def setUp(self):
        super().setUp()
        ensure_custom_fields()
        
        # Ensure we have a default Company
        if not frappe.db.get_default("Company"):
            company = frappe.new_doc("Company")
            company.company_name = "Test Company"
            company.default_currency = "INR"
            company.insert(ignore_permissions=True)
            
        # Ensure we have a Customer
        self.customer = frappe.db.get_value("Customer", {}, "name")
        if not self.customer:
            cust = frappe.new_doc("Customer")
            cust.customer_name = "Test Customer"
            cust.insert(ignore_permissions=True)
            self.customer = cust.name
            
        # Ensure we have a test user
        self.user = "test_user@example.com"
        if not frappe.db.exists("User", self.user):
            user_doc = frappe.new_doc("User")
            user_doc.email = self.user
            user_doc.first_name = "Test User"
            user_doc.send_welcome_email = 0
            user_doc.insert(ignore_permissions=True)
            
        # Link user to customer
        frappe.db.set_value("Customer", self.customer, "email_id", self.user)
        
        # Ensure we have a test item
        self.item = frappe.db.get_value("Item", {}, "name")
        if not self.item:
            item_doc = frappe.new_doc("Item")
            item_doc.item_code = "Test Medicine"
            item_doc.item_name = "Test Medicine"
            item_doc.item_group = "All Item Groups"
            item_doc.stock_uom = "Nos"
            item_doc.insert(ignore_permissions=True)
            self.item = item_doc.name

    def test_get_customer(self):
        customer = get_customer(self.user)
        self.assertEqual(customer, self.customer)

    def test_quotation_sync(self):
        # 1. Create a draft quotation representing the shopping cart
        q = get_active_quotation(self.customer, create_if_missing=True)
        self.assertIsNotNone(q)
        self.assertEqual(q.custom_shopping_cart, 1)
        
        # Clear existing items
        q.set("items", [])
        q.append("items", {
            "item_code": self.item,
            "qty": 3,
            "rate": 150.0
        })
        q.save(ignore_permissions=True)
        frappe.db.commit()
        
        # 2. Run sync to shopping cart
        sync_quotation_to_shopping_cart(self.user)
        
        # 3. Check that Shopping Cart has the item and correct qty
        cart_name = frappe.db.get_value("Shopping Cart", {"user": self.user, "status": "Open"})
        self.assertIsNotNone(cart_name)
        
        cart = frappe.get_doc("Shopping Cart", cart_name)
        self.assertEqual(len(cart.cart_items), 1)
        self.assertEqual(cart.cart_items[0].item, self.item)
        self.assertEqual(cart.cart_items[0].quantity, 3)
        self.assertEqual(cart.cart_items[0].rate, 150.0)
        self.assertEqual(cart.total_amount, 450.0)
        
        # 4. Modify Shopping Cart and sync back
        cart.cart_items[0].quantity = 5
        cart.save(ignore_permissions=True)
        sync_quotation_from_shopping_cart(cart)
        
        # 5. Check that Quotation was updated
        q.reload()
        self.assertEqual(len(q.items), 1)
        self.assertEqual(q.items[0].qty, 5)
