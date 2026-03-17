import frappe

def create_report():
    if not frappe.db.exists("Report", "Not Reported Sales"):
        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": "Not Reported Sales",
            "ref_doctype": "Tour Booking",
            "report_type": "Script Report",
            "is_standard": "Yes",
            "module": "Tourism App"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Report created successfully")
    else:
        print("Report already exists")
