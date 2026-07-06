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

            medicine = frappe.get_doc("Item", item_code)

            # Get Standard Selling Price
            medicine.standard_rate = frappe.db.get_value(
                "Item Price",
                {
                    "item_code": medicine.item_code,
                    "price_list": "Standard Selling"
                },
                "price_list_rate"
            ) or 0

            # Get Available Stock
            stock = frappe.db.sql("""
                SELECT COALESCE(SUM(actual_qty), 0)
                FROM `tabBin`
                WHERE item_code=%s
            """, medicine.item_code)[0][0]

            medicine.available_stock = stock

            context.medicine = medicine

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