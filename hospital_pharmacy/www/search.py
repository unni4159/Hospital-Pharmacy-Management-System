# pyrefly: ignore [missing-import]
import frappe

def get_context(context):
    search = frappe.form_dict.get("q")

    context.search = search

    if search:
        context.medicines = frappe.get_all(
            "Item",
            filters={
                "item_name": ["like", f"%{search}%"]
            },
            fields=[
                "item_code",
                "item_name",
                "standard_rate"
            ]
        )
    else:
        context.medicines = []