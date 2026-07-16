import frappe


no_cache = 1


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        context.cart = None
        context.payment_modes = []
        return context

    from hospital_pharmacy.api import sync_quotation_to_shopping_cart
    sync_quotation_to_shopping_cart(frappe.session.user)

    context.user = frappe.session.user

    # Get open shopping cart
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if not cart_name:
        context.cart = None
        return

    context.cart = frappe.get_doc("Shopping Cart", cart_name)
    context.payment_modes = frappe.get_all(
        "Mode of Payment",
        filters={"enabled": 1},
        fields=["name", "type"],
        order_by="name",
    )