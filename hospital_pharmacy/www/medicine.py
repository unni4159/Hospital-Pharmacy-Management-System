# import frappe

# def get_context(context):

#     name = frappe.form_dict.get("name")

#     if not name:
#         frappe.throw("Medicine not found.")

#     context.medicine = frappe.get_doc("Item", name)

import frappe


def get_context(context):

    name = frappe.form_dict.get("name")

    if not name:
        frappe.throw("Medicine not found.")

    medicine = frappe.get_doc("Item", name)

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
        WHERE item_code = %s
    """, medicine.item_code)[0][0]

    medicine.available_stock = stock

    context.medicine = medicine