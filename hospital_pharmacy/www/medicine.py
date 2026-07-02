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
        frappe.throw("Medicine not found")

    context.medicine = frappe.get_doc("Item", name)