@frappe.whitelist()
def create_order_from_cart(delivery_address, phone_number):

    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if not cart_name:
        frappe.throw("Shopping Cart is empty.")

    cart = frappe.get_doc("Shopping Cart", cart_name)

    if not cart.cart_items:
        frappe.throw("No items found in cart.")

    # Create Sales Invoice
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = cart.customer
    invoice.update_stock = 1

    for row in cart.cart_items:

        invoice.append("items", {
            "item_code": row.item,
            "qty": row.quantity,
            "rate": row.rate
        })

    invoice.insert(ignore_permissions=True)
    invoice.submit()

    # Create Delivery Order

    delivery = frappe.new_doc("Delivery Order")

    delivery.customer = cart.customer
    delivery.sales_invoice = invoice.name
    delivery.delivery_address = delivery_address
    delivery.phone_number = phone_number
    delivery.delivery_status = "Pending"

    delivery.insert(ignore_permissions=True)

    # Update Shopping Cart

    cart.status = "Ordered"
    cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "invoice": invoice.name,
        "delivery_order": delivery.name
    }