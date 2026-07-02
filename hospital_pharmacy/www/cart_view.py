import frappe


def get_context(context):

    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        }
    )

    if cart_name:
        context.cart = frappe.get_doc("Shopping Cart", cart_name)
    else:
        context.cart = None