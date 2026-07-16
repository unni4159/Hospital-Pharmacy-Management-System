import frappe

def get_context(context):

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login"
        return

    context.total_medicines = frappe.db.count("Item")

    context.total_customers = frappe.db.count("Customer")

    context.total_sales = frappe.db.count("Sales Invoice")

    context.total_suppliers = frappe.db.count("Supplier")