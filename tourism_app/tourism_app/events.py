import frappe

def sales_invoice_on_cancel(doc, method):
    if doc.custom_tour_booking:
        tour_booking_name = doc.custom_tour_booking
        # Cancel linked purchase invoices
        linked_pis = frappe.get_all("Purchase Invoice", filters={"custom_tour_booking": tour_booking_name, "docstatus": 1})
        for pi in linked_pis:
            pi_doc = frappe.get_doc("Purchase Invoice", pi.name)
            pi_doc.flags.ignore_si_check = True
            pi_doc.cancel()
        
        # Reset reporting state for Flight Ticket Item
        flights = frappe.get_all("Flight Ticket Item", filters={"sales_invoice": doc.name, "parent": tour_booking_name})
        for f in flights:
            frappe.db.set_value("Flight Ticket Item", f.name, {
                "is_reported": 0,
                "sales_invoice": None
            })
            
        # Reset reporting state for Hotel Reservation Item
        hotels = frappe.get_all("Hotel Reservation Item", filters={"sales_invoice": doc.name, "parent": tour_booking_name})
        for h in hotels:
            frappe.db.set_value("Hotel Reservation Item", h.name, {
                "is_reported": 0,
                "sales_invoice": None
            })
            
        # Remove sales invoice reference from Tour Booking if it matches
        current_si = frappe.db.get_value("Tour Booking", tour_booking_name, "sales_invoice_reference")
        if current_si == doc.name:
            frappe.db.set_value("Tour Booking", tour_booking_name, "sales_invoice_reference", None)

def purchase_invoice_on_cancel(doc, method):
    if getattr(doc.flags, "ignore_si_check", False):
        return
        
    if doc.custom_tour_booking:
        # Check if the linked Sales Invoice is cancelled
        # If the tour booking has a sales invoice, and it is NOT cancelled, show warning
        tour_booking = frappe.get_doc("Tour Booking", doc.custom_tour_booking)
        if tour_booking.sales_invoice_reference:
            si_status = frappe.db.get_value("Sales Invoice", tour_booking.sales_invoice_reference, "docstatus")
            if si_status != 2: # 2 means cancelled
                frappe.throw("Please cancel the linked Sales Invoice to maintain financial balance.", title="Warning")
