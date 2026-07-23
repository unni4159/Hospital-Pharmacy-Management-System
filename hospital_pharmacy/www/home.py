# pyrefly: ignore [missing-import]
import frappe

no_cache = 1

def get_context(context):
    context.user = frappe.session.user

    # Fetch featured medicines for homepage display
    items = frappe.get_all(
        "Item",
        filters={"disabled": 0, "is_stock_item": 1},
        fields=["name", "item_code", "item_name", "stock_uom", "image"],
        limit=8,
        order_by="creation desc"
    )

    featured_medicines = []
    for item in items:
        # Get Standard Selling Price
        price = frappe.db.get_value(
            "Item Price",
            {
                "item_code": item.item_code,
                "price_list": "Standard Selling"
            },
            "price_list_rate"
        ) or 0
        item.standard_rate = price

        # Get Available Stock
        stock = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty),0)
            FROM `tabBin`
            WHERE item_code=%s
        """, item.item_code)[0][0]
        item.available_stock = stock

        featured_medicines.append(item)

    context.featured_medicines = featured_medicines

    if frappe.session.user == "Guest":
        context.roles = []
        return context

    roles = frappe.get_roles(frappe.session.user)
    context.roles = roles

    # Administrator
    context.is_admin = "Administrator" in roles

    # Manager
    context.is_manager = (
        "Sales Manager" in roles or
        "Purchase Manager" in roles or
        "Stock Manager" in roles
    )

    # Pharmacist
    context.is_pharmacist = (
        "Sales User" in roles or
        "Stock User" in roles or
        "Purchase User" in roles
    )

    # Customer
    context.is_customer = "Customer" in roles