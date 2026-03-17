// Copyright (c) 2026, Admin and contributors
// For license information, please see license.txt

frappe.query_reports["Not Reported Sales"] = {
	"filters": [],
	get_datatable_options(options) {
		return Object.assign(options, {
			checkboxColumn: true,
		});
	},
	onload: function(report) {
		report.page.add_inner_button(__("Create Sales Invoice for Selected"), function() {
			let selected_rows = report.datatable.rowmanager.getSelectedRows();
			if (selected_rows.length === 0) {
				frappe.throw(__("Please select at least one row."));
			}

			let selected_data = selected_rows.map(idx => {
				let row = report.data[idx];
				return {
					name: row.name,
					item_type: row.item_type,
					booking_ref: row.booking_ref
				};
			});

			frappe.confirm(__("Create Sales Invoice for {0} selected items?", [selected_rows.length]), function() {
				frappe.call({
					method: "tourism_app.tourism_app.doctype.tour_booking.tour_booking.create_invoice_from_report",
					args: {
						selected_items: selected_data
					},
					callback: function(r) {
						if (r.message) {
							frappe.msgprint(r.message);
							report.refresh();
						}
					}
				});
			});
		});
	}
};
