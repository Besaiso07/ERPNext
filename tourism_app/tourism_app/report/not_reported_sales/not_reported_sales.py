# Copyright (c) 2026, Admin and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "item_type",
			"label": _("Item Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "name_desc",
			"label": _("Passenger / Hotel Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150
		},
		{
			"fieldname": "net_cost",
			"label": _("Net Cost"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "selling_price",
			"label": _("Selling Price"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "booking_ref",
			"label": _("Booking Ref"),
			"fieldtype": "Link",
			"options": "Tour Booking",
			"width": 150
		}
	]

def get_data(filters):
	data = []

	# Get Flights
	flights = frappe.db.get_all(
		"Flight Ticket Item",
		filters={"is_reported": 0},
		fields=["name", "pax_name", "airline_supplier", "net_purchase_price", "selling_price", "parent"]
	)
	
	for f in flights:
		data.append({
			"name": f.name,
			"item_type": "Flight Ticket",
			"name_desc": f.pax_name,
			"supplier": f.airline_supplier,
			"net_cost": f.net_purchase_price,
			"selling_price": f.selling_price,
			"booking_ref": f.parent
		})

	# Get Hotels
	hotels = frappe.db.get_all(
		"Hotel Reservation Item",
		filters={"is_reported": 0},
		fields=["name", "hotel_name", "hotel_supplier", "purchase_price", "selling_price", "parent"]
	)

	for h in hotels:
		data.append({
			"name": h.name,
			"item_type": "Hotel Reservation",
			"name_desc": h.hotel_name,
			"supplier": h.hotel_supplier,
			"net_cost": h.purchase_price,
			"selling_price": h.selling_price,
			"booking_ref": h.parent
		})

	return data
