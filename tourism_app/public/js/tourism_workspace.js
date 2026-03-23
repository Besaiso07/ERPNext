$(document).on('app_ready', function() {
    // Inject custom workspace logic
    frappe.router.on('change', function() {
        if (frappe.get_route_str() === 'Workspaces/Tourism' || frappe.get_route_str() === 'tourism') {
            setTimeout(add_upload_button_to_workspace, 500);
        }
    });

    // Global interceptor for Shortcut click
    $(document).off('click', '.shortcut-item-wrapper[data-label="Upload Ticket (AIR File)"]');
    $(document).on('click', '.shortcut-item-wrapper[data-label="Upload Ticket (AIR File)"]', function(e) {
        e.preventDefault();
        e.stopPropagation();
        trigger_customer_selection();
    });
});

function add_upload_button_to_workspace() {
    if ($('.page-head .page-title:contains("Tourism")').length) {
        if ($('.btn-upload-air').length === 0) {
            let btn = $('<button class="btn btn-primary btn-sm btn-upload-air" style="margin-left: 10px;">')
                .append('<i class="fa fa-upload"></i> ' + __("Upload Ticket (AIR File)"))
                .click(function() {
                    trigger_customer_selection();
                });
            $('.page-head .page-actions').prepend(btn);
        }
    }
}

function trigger_customer_selection() {
    let d = new frappe.ui.Dialog({
        title: __("Select Customer for AIR Import"),
        fields: [
            {
                label: __("Customer (Optional)"),
                fieldname: "customer",
                fieldtype: "Link",
                options: "Customer",
                description: __("Leave blank to auto-detect from AIR file code (RM*AN)")
            }
        ],
        primary_action_label: __("Proceed to Upload"),
        primary_action(values) {
            d.hide();
            trigger_air_upload(values.customer);
        }
    });
    d.show();
}

function trigger_air_upload(customer) {
    new frappe.ui.FileUploader({
        on_success: (file_doc) => {
            console.log("File Uploaded successfully:", file_doc.file_url);
            
            // Trigger the AIR Processing after successful upload
            frappe.call({
                method: 'tourism_app.tourism_app.api.process_air_file',
                args: {
                    file_url: file_doc.file_url,
                    customer: customer
                },
                freeze: true,
                freeze_message: __("Parsing AIR File and Creating Booking..."),
                callback: function(r) {
                    if (!r.exc && r.message) {
                        console.log("AIR Processed. Tour Booking ID:", r.message);
                        frappe.set_route('Form', 'Tour Booking', r.message);
                    }
                }
            });
        }
    });
}
