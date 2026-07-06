# import frappe

# def get_context(context):

#     context.title = "Available Medicines"

#     search = frappe.form_dict.get("search")

#     filters = {
#         "disabled": 0,
#         "is_stock_item": 1
#     }

#     if search:
#         items = frappe.get_all(
#             "Item",
#             filters=filters,
#             or_filters={
#                 "item_name": ["like", f"%{search}%"],
#                 "item_code": ["like", f"%{search}%"]
#             },
#             fields=[
#                 "name",
#                 "item_code",
#                 "item_name",
#                 "stock_uom",
#                 "standard_rate",
#                 "image"
#             ],
#             order_by="item_name asc"
#         )
#     else:
#         items = frappe.get_all(
#             "Item",
#             filters=filters,
#             fields=[
#                 "name",
#                 "item_code",
#                 "item_name",
#                 "stock_uom",
#                 "standard_rate",
#                 "image"
#             ],
#             order_by="item_name asc"
#         )

#     medicines = []

#     for item in items:

#         stock = frappe.db.sql("""
#             SELECT SUM(actual_qty)
#             FROM `tabBin`
#             WHERE item_code=%s
#         """, item.item_code)[0][0] or 0

#         item.available_stock = stock
#         medicines.append(item)

#     context.medicines = medicines
#     context.search = search or ""








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
                "image"
            ],
            order_by="item_name asc"
        )

    medicines = []

    for item in items:

        # Get Standard Selling Price
        price = frappe.db.get_value(
            "Item Price",
            {
                "item_code": item.item_code,
                "price_list": "Standard Selling"
            },
            "price_list_rate"
        ) or 0

        item.standard_rate = price

        # Get Available Stock
        stock = frappe.db.sql("""
            SELECT COALESCE(SUM(actual_qty),0)
            FROM `tabBin`
            WHERE item_code=%s
        """, item.item_code)[0][0]

        item.available_stock = stock

        medicines.append(item)

    context.medicines = medicines
    context.search = search or ""