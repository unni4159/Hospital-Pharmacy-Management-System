import frappe


no_cache = 1


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        context.cart = None
        return context

    context.error = frappe.form_dict.get("error")

    from hospital_pharmacy.api import sync_quotation_to_shopping_cart
    sync_quotation_to_shopping_cart(frappe.session.user)

    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if cart_name:
        cart = frappe.get_doc("Shopping Cart", cart_name)
        for row in cart.cart_items:
            item_info = frappe.db.get_value("Item", row.item, ["item_name", "image"], as_dict=True) or {}
            row.item_name = item_info.get("item_name") or row.item
            row.image = item_info.get("image")
            stock = frappe.db.sql("""
                SELECT COALESCE(SUM(actual_qty), 0)
                FROM `tabBin`
                WHERE item_code=%s
            """, row.item)[0][0]
            row.available_stock = stock
        context.cart = cart
    else:
        context.cart = None
