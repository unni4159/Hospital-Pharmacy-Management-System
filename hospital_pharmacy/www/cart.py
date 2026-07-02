import frappe


def get_context(context):

    # Logged in user
    context.user = frappe.session.user

    # Selected item from URL
    item_code = frappe.form_dict.get("item")

    context.selected_item = item_code
    context.medicine = None
    context.error = None

    # Check if item parameter exists
    if item_code:

        if frappe.db.exists("Item", item_code):
            context.medicine = frappe.get_doc("Item", item_code)
        else:
            context.error = "Selected medicine does not exist."

    else:
        context.error = "No medicine selected."

    # Load current user's open shopping cart
    context.cart = None

    if frappe.session.user != "Guest":

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

    return context