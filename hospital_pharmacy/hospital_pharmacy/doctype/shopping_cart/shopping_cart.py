# # Copyright (c) 2026, UK and contributors
# # For license information, please see license.txt

# # import frappe
# from frappe.model.document import Document


# class ShoppingCart(Document):
# 	pass



# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.model.document import Document
# pyrefly: ignore [missing-import]
from frappe.utils import today


class ShoppingCart(Document):

    def on_update(self):
        pass

    def on_trash(self):
        pass

    # ==========================================================
    # CREATE / UPDATE DRAFT SALES ORDER
    # ==========================================================
    def sync_sales_order_draft(self):

        if not self.customer:
            return

        if self.status != "Open" or not self.cart_items:
            self.delete_draft_sales_order()
            return

        # If a submitted Sales Order already exists for this cart, skip syncing draft
        if frappe.db.exists("Sales Order", {"po_no": f"Shopping Cart: {self.name}", "docstatus": 1}):
            return

        sales_order_name = frappe.db.get_value(
            "Sales Order",
            {
                "customer": self.customer,
                "docstatus": 0,
                "po_no": f"Shopping Cart: {self.name}"
            },
            "name"
        )

        if sales_order_name:
            so = frappe.get_doc("Sales Order", sales_order_name)
            so.set("items", [])
        else:
            so = frappe.new_doc("Sales Order")
            so.customer = self.customer
            so.company = frappe.db.get_default("Company")
            so.po_no = f"Shopping Cart: {self.name}"
            so.transaction_date = today()
            so.delivery_date = today()

        # ERPNext resolves Customer defaults during this server-managed sync.
        # Document-level bypass keeps the request's portal-user session intact.
        so.flags.ignore_permissions = True

        for item in self.cart_items:
            so.append("items", {
                "item_code": item.item,
                "qty": item.quantity,
                "rate": item.rate,
                "delivery_date": today()
            })

        so.run_method("set_missing_values")
        so.save(ignore_permissions=True)

    # ==========================================================
    # DELETE DRAFT SALES ORDER
    # ==========================================================
    def delete_draft_sales_order(self):

        if not self.customer:
            return

        sales_order_name = frappe.db.get_value(
            "Sales Order",
            {
                "customer": self.customer,
                "docstatus": 0,
                "po_no": f"Shopping Cart: {self.name}"
            },
            "name"
        )

        if sales_order_name:

            frappe.delete_doc(
                "Sales Order",
                sales_order_name,
                ignore_permissions=True
            )
