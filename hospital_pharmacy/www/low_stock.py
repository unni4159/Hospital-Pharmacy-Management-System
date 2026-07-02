import frappe

def get_context(context):
    stock_items = frappe.get_all(
        "Item",
        filters={"is_stock_item": 1},
        fields=["item_code", "item_name", "stock_uom"]
    )

    for item in stock_items:
        qty = frappe.db.sql("""
            SELECT IFNULL(SUM(actual_qty), 0)
            FROM `tabStock Ledger Entry`
            WHERE item_code = %s
        """, item.item_code)[0][0]

        item.available_stock = qty

    context.stock_items = stock_items