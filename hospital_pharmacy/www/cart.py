import frappe


no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        item_code = frappe.form_dict.get("item")
        if item_code:
            frappe.local.response["location"] = f"/login?redirect-to=/cart?item={item_code}"
        else:
            frappe.local.response["location"] = "/login"
        context.user = "Guest"
        context.selected_item = item_code
        context.medicine = None
        context.error = None
        context.cart = None
        return context

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

    # Load the logged-in customer's active draft quotation.  The template
    # keeps the existing `cart` context name, so its layout and actions do
    # not need to change while the data source is now Quotation -> items.
    context.cart = None

    if frappe.session.user != "Guest":
        from hospital_pharmacy.api import get_active_quotation, get_customer

        customer = get_customer(frappe.session.user)
        if customer:
            context.cart = get_active_quotation(customer)

    return context
