// Copyright (c) 2026, Tourism App and contributors
// For license information, please see license.txt

frappe.ui.form.on('Tour Booking', {
    refresh: function(frm) {
        // Show "Create Sales Invoice" button if no reference exists and document is saved
        if (!frm.doc.__islocal && !frm.doc.sales_invoice_reference) {
            frm.add_custom_button(__('Create Sales Invoice'), function() {
                frappe.call({
                    method: 'create_sales_invoice',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Creating Invoices...'),
                    callback: function(r) {
                        if (!r.exc && r.message) {
                            frm.reload_doc();
                            frappe.set_route('Form', 'Sales Invoice', r.message);
                        }
                    }
                });
            }).addClass('btn-primary');
        }

        // Show "Unlink Invoice" button if reference exists
        if (!frm.doc.__islocal && frm.doc.sales_invoice_reference) {
            frm.add_custom_button(__('Unlink Invoice'), function() {
                frappe.db.get_value('Sales Invoice', frm.doc.sales_invoice_reference, 'docstatus', function(r) {
                    if (r && r.docstatus === 2) {
                        frm.set_value('sales_invoice_reference', '');
                        frm.save().then(() => {
                            frm.reload_doc();
                        });
                    } else {
                        frappe.msgprint(__('You must Cancel the linked Sales Invoice in the Accounting module before unlinking it here.'));
                    }
                });
            }).addClass('btn-danger');
        }
    }
});

frappe.ui.form.on('Flight Ticket Item', {
    flight_route: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.flight_route) {
            // 1. Formatting Logic (Uppercase + Auto-dash)
            let val = row.flight_route.toUpperCase();
            let clean_val = val.replace(/[^A-Z]/g, '');
            let segments = [];
            
            // Chunk into 3s
            for (let i = 0; i < clean_val.length; i += 3) {
                segments.push(clean_val.substring(i, i + 3));
            }

            // 2. Validation / Auto-delete Logic
            let valid_segments = [];
            let check_promises = segments.map(code => {
                if (code.length === 3) {
                    return frappe.db.exists('Airport', code).then(exists => {
                        if (exists) {
                            valid_segments.push(code);
                        } else {
                            frappe.show_alert({
                                message: `خطأ: كود المطار (${code}) غير موجود! تم حذفه تلقائياً.`,
                                indicator: 'red'
                            }, 5);
                        }
                    });
                } else {
                    // If it's incomplete (1 or 2 letters), keep it for now so user can finish typing
                    valid_segments.push(code);
                    return Promise.resolve();
                }
            });

            Promise.all(check_promises).then(() => {
                let formatted = valid_segments.join('-');
                if (row.flight_route !== formatted) {
                    frappe.model.set_value(cdt, cdn, 'flight_route', formatted);
                }
            });
        }
    }
});
