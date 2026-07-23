import frappe

def run():
    frappe.set_user("Administrator")
    open_carts = frappe.get_all(
        "Shopping Cart",
        filters={"status": "Open"},
        fields=["name", "user", "customer"]
    )
    print("Open carts:")
    for cart in open_carts:
        doc = frappe.get_doc("Shopping Cart", cart.name)
        items = [(item.item, item.quantity) for item in doc.cart_items]
        print(f"  Cart: {cart.name}, User: {cart.user}, Customer: {cart.customer}, Items: {items}")
