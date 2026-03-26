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

        // Show "Update All Linked Invoices" button if reference exists
        if (!frm.doc.__islocal && frm.doc.sales_invoice_reference) {
            frm.add_custom_button(__('Update All Linked Invoices'), function() {
                frappe.call({
                    method: 'tourism_app.tourism_app.doctype.tour_booking.tour_booking.manual_sync_invoices',
                    args: {
                        docname: frm.doc.name
                    },
                    freeze: true,
                    freeze_message: __('Syncing Invoices...'),
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc();
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

        // Show "Import AIR File Content" button
        frm.add_custom_button(__('Import AIR File Content'), function() {
            let d = new frappe.ui.Dialog({
                title: __('Paste AIR File Content'),
                fields: [
                    {
                        label: __('AIR Content'),
                        fieldname: 'air_content',
                        fieldtype: 'Small Text',
                        reqd: 1
                    }
                ],
                primary_action_label: __('Import'),
                primary_action(values) {
                    frappe.call({
                        method: 'tourism_app.tourism_app.doctype.tour_booking.tour_booking.import_air_file',
                        args: {
                            content: values.air_content,
                            docname: frm.doc.name
                        },
                        freeze: true,
                        freeze_message: __('Parsing AIR File...'),
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                                d.hide();
                                frappe.show_alert({
                                    message: __('AIR File Content Imported successfully!'),
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                }
            });
            d.show();
        });

        // Show "Import Ticket File" button (Actual file upload)
        frm.add_custom_button(__('Import Ticket (AIR/PDF)'), function() {
            let d = new frappe.ui.Dialog({
                title: __('Upload Ticket File'),
                fields: [
                    {
                        label: __('Customer (Optional)'),
                        fieldname: 'customer',
                        fieldtype: 'Link',
                        options: 'Customer',
                        description: __('Leave blank if the AIR file contains an RM*AN code.')
                    },
                    {
                        label: __('Ticket File'),
                        fieldname: 'air_file',
                        fieldtype: 'Attach',
                        reqd: 1,
                        description: __('Upload the .txt (AIR) or .pdf (MedSky) ticket file.')
                    }
                ],
                primary_action_label: __('Process & Create Booking'),
                primary_action(values) {
                    if (!values.air_file) {
                        frappe.msgprint(__('Please attach a file.'));
                        return;
                    }
                    d.hide();
                    frappe.call({
                        method: 'tourism_app.tourism_app.api.process_air_file',
                        args: {
                            file_url: values.air_file,
                            customer: values.customer || ''
                        },
                        freeze: true,
                        freeze_message: __('Processing File...'),
                        callback: function(r) {
                            if (r.message) {
                                frappe.set_route('Form', 'Tour Booking', r.message);
                            }
                        }
                    });
                }
            });
            d.show();
        });

        update_live_margin(frm);
    },
    supplier_currency: function(frm) {
        if (frm.doc.supplier_currency) {
            frappe.call({
                method: 'tourism_app.tourism_app.doctype.tour_booking.tour_booking.get_exchange_rate',
                args: { from_currency: frm.doc.supplier_currency },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('supplier_exchange_rate', r.message);
                    }
                }
            });
        }
    },
    customer_currency: function(frm) {
        if (frm.doc.customer_currency) {
            frappe.call({
                method: 'tourism_app.tourism_app.doctype.tour_booking.tour_booking.get_exchange_rate',
                args: { from_currency: frm.doc.customer_currency },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('customer_exchange_rate', r.message);
                    }
                }
            });
        }
    }
});

function update_live_margin(frm) {
    let rev_lyd = 0;
    let cost_lyd = 0;
    let currency_costs = {};

    (frm.doc.flights || []).forEach(f => {
        let f_curr = f.currency || 'LYD';
        let f_net_foreign = (f.fare || 0) + (f.tax || 0) - (f.supplier_commission || 0);
        
        currency_costs[f_curr] = (currency_costs[f_curr] || 0) + f_net_foreign;
        cost_lyd += (f.base_currency_amount || 0);
        rev_lyd += (f.fare || 0) + (f.tax || 0) + (f.agency_markup || 0);
    });

    (frm.doc.hotels || []).forEach(h => {
        let h_curr = h.currency || 'LYD';
        currency_costs[h_curr] = (currency_costs[h_curr] || 0) + (h.purchase_price || 0);
        cost_lyd += (h.base_purchase_price || h.purchase_price || 0);
        rev_lyd += (h.purchase_price || 0) + (h.agency_markup || 0);
    });

    let profit = rev_lyd - cost_lyd;
    let color = profit >= 0 ? 'green' : 'red';
    
    // Build currency breakdown string
    let breakdown = Object.keys(currency_costs).map(curr => {
        return `${curr}: <b>${currency_costs[curr].toFixed(2)}</b>`;
    }).join(' | ');

    let html = `<div style="padding: 12px; background-color: #fcfcfc; border-radius: 8px; border: 1px solid #eee; border-left: 5px solid ${color}; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
        <div style="font-size: 1.1em; margin-bottom: 8px;">
            <strong>Financial Summary:</strong>
        </div>
        <div style="margin-bottom: 5px;">
            <span style="color: #666;">Total Revenue (LYD):</span> <b>${rev_lyd.toFixed(2)}</b>
        </div>
        <div style="margin-bottom: 5px;">
            <span style="color: #666;">Cost Breakdown:</span> ${breakdown}
        </div>
        <div style="margin-top: 10px; border-top: 1px dashed #eee; padding-top: 8px; font-size: 1.2em;">
            <strong>Final Profit (Equivalent LYD):</strong> <span style="color: ${color}; font-weight: bold;">${profit.toFixed(2)}</span>
        </div>
    </div>`;
    
    frm.dashboard.set_headline(html);
}

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
    },
    fare: function(frm, cdt, cdn) { calculate_flight_totals(frm, cdt, cdn); },
    tax: function(frm, cdt, cdn) { calculate_flight_totals(frm, cdt, cdn); },
    commission_type: function(frm, cdt, cdn) { calculate_flight_totals(frm, cdt, cdn); },
    commission_rate: function(frm, cdt, cdn) { calculate_flight_totals(frm, cdt, cdn); },
    agency_markup: function(frm, cdt, cdn) { calculate_flight_totals(frm, cdt, cdn); }
});

function calculate_flight_totals(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let fare = flt(row.fare);
    let tax = flt(row.tax);
    let comm_rate = flt(row.commission_rate);
    let std_comm = 0;
    
    if (row.commission_type === 'Fixed Amount') {
        std_comm = comm_rate;
    } else { // Default to percentage
        std_comm = fare * (comm_rate / 100);
    }
    
    let net_cost = fare + tax - std_comm;
    let selling = fare + tax + flt(row.agency_markup);
    let profit = selling - net_cost;

    frappe.model.set_value(cdt, cdn, {
        supplier_commission: std_comm,
        net_purchase_price: net_cost,
        selling_price: selling,
        profit: profit
    });

    update_live_margin(frm);
}

frappe.ui.form.on('Hotel Reservation Item', {
    purchase_price: function(frm) { update_live_margin(frm); },
    agency_markup: function(frm) { update_live_margin(frm); }
});
