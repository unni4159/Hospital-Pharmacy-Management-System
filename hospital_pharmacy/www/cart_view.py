import frappe


no_cache = 1


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        context.cart = None
        return context

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
        context.cart = frappe.get_doc("Shopping Cart", cart_name)
    else:
        context.cart = None
