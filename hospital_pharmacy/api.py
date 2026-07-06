import frappe
from frappe.utils import today


# ==========================================================
# ADD TO CART
# ==========================================================

@frappe.whitelist()
def add_to_cart(item_code, qty=1):

    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    qty = int(qty)

    if qty <= 0:
        frappe.throw("Quantity must be greater than zero.")

    # Get Item
    item = frappe.get_doc("Item", item_code)

    # Get Available Stock
    stock = frappe.db.sql("""
        SELECT COALESCE(SUM(actual_qty),0)
        FROM `tabBin`
        WHERE item_code=%s
    """, item_code)[0][0]

    if stock <= 0:
        frappe.throw("This medicine is currently Out of Stock.")

    if qty > stock:
        frappe.throw(f"Only {stock} item(s) available in stock.")

    # Get Selling Price
    rate = frappe.db.get_value(
        "Item Price",
        {
            "item_code": item_code,
            "price_list": "Standard Selling"
        },
        "price_list_rate"
    )

    if not rate:
        frappe.throw(f"Standard Selling Price not found for {item.item_name}")

    # Get Customer
    customer = frappe.db.get_value("Customer", {}, "name")

    if not customer:
        frappe.throw("No Customer found.")

    # Existing Cart
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
        cart.user = frappe.session.user
        cart.customer = customer
        cart.status = "Open"
        cart.order_date = today()

    found = False

    for row in cart.cart_items:

        if row.item == item.name:

            new_qty = row.quantity + qty

            if new_qty > stock:
                frappe.throw(
                    f"Only {stock} item(s) available for {item.item_name}."
                )

            row.quantity = new_qty
            row.rate = rate
            row.amount = row.quantity * row.rate

            found = True
            break

    if not found:

        cart.append("cart_items", {
            "item": item.name,
            "quantity": qty,
            "rate": rate,
            "amount": qty * rate
        })

    # Calculate Total
    total = 0

    for row in cart.cart_items:
        row.amount = row.quantity * row.rate
        total += row.amount

    cart.total_amount = total

    cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Item added to cart successfully.",
        "cart": cart.name
    }


# ==========================================================
# CREATE ORDER FROM SHOPPING CART
# ==========================================================

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

    # ===========================================
    # Validate Stock Before Creating Invoice
    # ===========================================

    for row in cart.cart_items:

        stock = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty),0)
            FROM `tabBin`
            WHERE item_code=%s
        """, row.item)[0][0]

        if stock <= 0:
            frappe.throw(f"{row.item} is Out of Stock.")

        if row.quantity > stock:
            frappe.throw(
                f"Only {stock} quantity available for {row.item}."
            )

    # ===========================================
    # Create Sales Invoice
    # ===========================================

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

    # ===========================================
    # Create Delivery Order
    # ===========================================

    delivery = frappe.new_doc("Delivery Order")

    delivery.customer = cart.customer
    delivery.sales_invoice = invoice.name
    delivery.delivery_address = delivery_address
    delivery.phone_number = phone_number
    delivery.delivery_status = "Pending"

    delivery.insert(ignore_permissions=True)

    # ===========================================
    # Close Shopping Cart
    # ===========================================

    cart.status = "Ordered"
    cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "invoice": invoice.name,
        "delivery_order": delivery.name,
        "message": "Order placed successfully."
    }


    # ==========================================================
# REMOVE ITEM FROM SHOPPING CART
# ==========================================================

@frappe.whitelist()
def remove_from_cart(item_code):

    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    # Get Open Cart
    cart_name = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user,
            "status": "Open"
        },
        "name"
    )

    if not cart_name:
        frappe.throw("Shopping Cart not found.")

    cart = frappe.get_doc("Shopping Cart", cart_name)

    found = False

    # Remove Selected Item
    for row in list(cart.cart_items):
        if row.item == item_code:
            cart.remove(row)
            found = True
            break

    if not found:
        frappe.throw("Item not found in cart.")

    # Recalculate Total
    total = 0

    for row in cart.cart_items:
        row.amount = row.quantity * row.rate
        total += row.amount

    cart.total_amount = total

    # If Cart Becomes Empty
    if len(cart.cart_items) == 0:
        cart.total_amount = 0

    cart.save(ignore_permissions=True)

    frappe.db.commit()

    return {
        "status": "success",
        "message": "Item removed successfully."
    }