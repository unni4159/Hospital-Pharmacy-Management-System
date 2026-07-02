import frappe


def get_context(context):

    # User must be logged in
    if frappe.session.user == "Guest":
        frappe.throw("Please login first.")

    invoice_name = frappe.form_dict.get("invoice")

    if not invoice_name:
        frappe.throw("Invoice not found.")

    # Get customer linked with logged-in user
    customer = frappe.db.get_value(
        "Shopping Cart",
        {
            "user": frappe.session.user
        },
        "customer"
    )

    if not customer:
        frappe.throw("Customer not found.")

    # Verify invoice belongs to this customer
    invoice_customer = frappe.db.get_value(
        "Sales Invoice",
        invoice_name,
        "customer"
    )

    if invoice_customer != customer:
        frappe.throw("You are not permitted to view this order.")

    context.invoice = frappe.get_doc("Sales Invoice", invoice_name)