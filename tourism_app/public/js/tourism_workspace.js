$(document).on('app_ready', function() {
    // 1. PHASE 38.2: NUCLEAR UI RESET (English, No Sidebar, No Icons)
    const setupNuclearUI = () => {
        const host = window.location.host;
        if (!host.includes("test.localhost") && !host.includes("127.0.0.1")) return;

        // Force CSS
        if (!$("#phase-38-css").length) {
            $("<style id='phase-38-css'>").text(`
                .layout-side-bar, .layout-side-section, .sidebar-toggle, .desk-sidebar { 
                    display: none !important; width: 0 !important; visibility: hidden !important; 
                }
                .layout-main-section { width: 100% !important; margin-left: 0 !important; padding-top: 50px !important; }
                .navbar { top: 30px !important; }
                
                #p38-menu-container { display: flex; align-items: center; justify-content: center; flex: 1; gap: 25px; }
                .p3 category { position: relative; color: #1b4f72; font-weight: 800; cursor: pointer; font-size: 14px; }
                .p3-dropdown { 
                    display: none; position: absolute; top: 100%; left: 0; 
                    background: white; border: 1px solid #ddd; border-radius: 4px; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.1); min-width: 160px; z-index: 1000;
                }
                .p3-category:hover .p3-dropdown { display: block; }
                .p3-link { display: block; padding: 10px 15px; color: #1b4f72; font-weight: 600; text-decoration: none !important; font-size: 13px; }
                .p3-link:hover { background: #f5f7fa; }
            `).appendTo("head");
        }

        // Branding Update
        $(".navbar-brand").html('<b style="color: #1b4f72; font-size: 1.1rem;">TOURISM PORTAL</b>');

        // English Menu Injection
        if (!document.getElementById("p38-menu-container")) {
            const menu = $(`
                <div id="p38-menu-container">
                    <div class="p3-category">FRONT OFFICE
                        <div class="p3-dropdown">
                            <a class="p3-link" href="/app/tour-booking/new-tour-booking">Single Ticket</a>
                        </div>
                    </div>
                    <div class="p3-category">MASTER
                        <div class="p3-dropdown">
                            <a class="p3-link" href="/app/customer">Customer</a>
                            <a class="p3-link" href="/app/supplier">Supplier</a>
                        </div>
                    </div>
                    <div class="p3-category">BACK OFFICE
                        <div class="p3-dropdown">
                            <a class="p3-link" href="/app/sales-invoice">Invoice</a>
                        </div>
                    </div>
                    <div class="p3-category">REPORTS
                        <div class="p3-dropdown">
                            <a class="p3-link" href="/app/report">General Reports</a>
                        </div>
                    </div>
                </div>
            `);
            $(".navbar-collapse").append(menu);
        }

        // SAFETY: Kill old Arabic menus if they re-render
        $("#custom-top-menu, #custom-navbar-menu, #english-nav, #professional-menu").remove();
        $(".layout-side-bar, .layout-side-section, .navbar-brand i").remove();
    };

    setupNuclearUI();
    setInterval(setupNuclearUI, 500);

    // 2. EXISTING TOURISM WORKSPACE LOGIC
    frappe.router.on('change', function() {
        if (frappe.get_route_str() === 'Workspaces/Tourism' || frappe.get_route_str() === 'tourism') {
            setTimeout(add_upload_button_to_workspace, 500);
        }
    });

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
            frappe.call({
                method: 'tourism_app.tourism_app.api.process_air_file',
                args: { file_url: file_doc.file_url, customer: customer },
                freeze: true,
                freeze_message: __("Parsing AIR File..."),
                callback: function(r) {
                    if (!r.exc && r.message) {
                        frappe.set_route('Form', 'Tour Booking', r.message);
                    }
                }
            });
        }
    });
}
