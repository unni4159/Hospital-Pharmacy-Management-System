import frappe
from frappe.utils import today


def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    item_code = frappe.form_dict.get("item")
    quantity = int(frappe.form_dict.get("qty") or 1)

    if not item_code:
        frappe.throw("Medicine not selected.")

    item = frappe.get_doc("Item", item_code)

    # For now use the first customer (you can improve this later)
    customer = frappe.db.get_value("Customer", {}, "name")

    if not customer:
        frappe.throw("Please create a Customer first.")

    # Find existing open cart
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
    else:
        cart = frappe.new_doc("Shopping Cart")
        cart.customer = customer
        cart.user = frappe.session.user
        cart.status = "Open"
        cart.order_date = today()

    # Update existing item if present
    found = False

    for row in cart.cart_items:
        if row.item == item.name:
            row.quantity += quantity
            found = True
            break

    if not found:
        cart.append("cart_items", {
            "item": item.name,
            "quantity": quantity,
            "rate": item.standard_rate,
            "amount": quantity * item.standard_rate
        })

    total = 0

    for row in cart.cart_items:
        row.amount = row.quantity * row.rate
        total += row.amount

    cart.total_amount = total

    cart.save(ignore_permissions=True)
    frappe.db.commit()

    # Redirect to cart view
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/cart_view"