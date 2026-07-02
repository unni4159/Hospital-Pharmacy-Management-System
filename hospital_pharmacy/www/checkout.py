import frappe


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.throw("Please login to place an order.")

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