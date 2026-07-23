# pyrefly: ignore [missing-import]
import frappe
# pyrefly: ignore [missing-import]
from frappe.utils import today


def get_context(context):

    context.today = today()

    context.medicines = frappe.get_all(
        "Batch",
        filters={
            "expiry_date": ["<=", today()]
        },
        fields=[
            "name",
            "item",
            "expiry_date"
        ],
        order_by="expiry_date asc"
    )