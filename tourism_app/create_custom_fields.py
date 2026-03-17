import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def create_fields():
    if not frappe.db.exists("Custom Field", "Purchase Invoice-custom_tour_booking"):
        create_custom_field("Purchase Invoice", {
            "fieldname": "custom_tour_booking",
            "label": "Tour Booking",
            "fieldtype": "Data",
            "insert_after": "naming_series",
            "read_only": 1
        })
        print("Created custom field for Purchase Invoice")
    
    if not frappe.db.exists("Custom Field", "Sales Invoice-custom_tour_booking"):
        create_custom_field("Sales Invoice", {
            "fieldname": "custom_tour_booking",
            "label": "Tour Booking",
            "fieldtype": "Data",
            "insert_after": "naming_series",
            "read_only": 1
        })
        print("Created custom field for Sales Invoice")
