import frappe

def get_context(context):

    context.title = "Available Medicines"

    search = frappe.form_dict.get("search")

    filters = {
        "disabled": 0,
        "is_stock_item": 1
    }

    if search:
        items = frappe.get_all(
            "Item",
            filters=filters,
            or_filters={
                "item_name": ["like", f"%{search}%"],
                "item_code": ["like", f"%{search}%"]
            },
            fields=[
                "name",
                "item_code",
                "item_name",
                "stock_uom",
                "standard_rate",
                "image"
            ],
            order_by="item_name asc"
        )
    else:
        items = frappe.get_all(
            "Item",
            filters=filters,
            fields=[
                "name",
                "item_code",
                "item_name",
                "stock_uom",
                "standard_rate",
                "image"
            ],
            order_by="item_name asc"
        )

    medicines = []

    for item in items:

        stock = frappe.db.sql("""
            SELECT SUM(actual_qty)
            FROM `tabBin`
            WHERE item_code=%s
        """, item.item_code)[0][0] or 0

        item.available_stock = stock
        medicines.append(item)

    context.medicines = medicines
    context.search = search or ""