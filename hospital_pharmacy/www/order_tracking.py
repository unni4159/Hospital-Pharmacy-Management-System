# pyrefly: ignore [missing-import]
import frappe

no_cache = 1

def get_context(context):
    context.is_admin = False
    context.user_roles = frappe.get_roles()
    
    if "System Manager" in context.user_roles or frappe.session.user == "Administrator":
        context.is_admin = True

    context.default_order_id = ""
    context.orders = []
    if frappe.session.user != "Guest":
        customer = frappe.db.get_value("Shopping Cart", {"user": frappe.session.user}, "customer")
        if customer:
            latest_do = frappe.db.get_value(
                "Delivery Order",
                {"customer": customer},
                "sales_invoice",
                order_by="creation desc"
            )
            if latest_do:
                context.default_order_id = latest_do
            
            # Fetch all tracked invoices for this customer
            tracked_invoices = [
                x.sales_invoice for x in frappe.get_all(
                    "Delivery Order",
                    filters={"customer": customer},
                    fields=["sales_invoice"]
                ) if x.sales_invoice
            ]
            
            if tracked_invoices:
                orders = frappe.get_all(
                    "Sales Invoice",
                    filters={"name": ["in", tracked_invoices]},
                    fields=["name", "posting_date", "grand_total", "status"],
                    order_by="creation desc"
                )
                for order in orders:
                    items = frappe.get_all(
                        "Sales Invoice Item",
                        filters={"parent": order.name},
                        fields=["item_code", "item_name"]
                    )
                    for item in items:
                        item.image = frappe.db.get_value("Item", {"item_code": item.item_code}, "image") or ""
                    order.order_items = items
                context.orders = orders
