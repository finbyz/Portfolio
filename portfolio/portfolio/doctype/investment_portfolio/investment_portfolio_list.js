let imports_in_progress = [];

frappe.listview_settings['Investment Portfolio'] = {

    refresh: function (listview) {
		listview.page.add_inner_button(__("Apply Bonus"), function () {
			show_bonus_dialog(listview);
		});
	},

	add_fields: ['status','qty','pending_qty',"docstatus"],
	get_indicator: function(doc) {
        
	    if(doc.pending_qty==doc.qty){
            return [__("Holding"), "orange", "status,=,Holding"];
        }
        if(doc.pending_qty == 0){
            return [__("Exited"), "grey", "status,=, Exited"];
        }
        if(doc.qty!=doc.pending_qty){
            return [__("Partially Exited"), "red", "status,=,Partially Exited"];
      }

	},
   
	hide_name_column: true
};

function calculate_post_bonus_preview(dialog) {
    let holding_qty = flt(dialog.get_value("holding_qty"));
    let ratio = flt(dialog.get_value("ratio"));
    if (holding_qty && ratio) {
        dialog.set_value("post_bonus_qty", holding_qty + holding_qty * ratio);
    } else {
        dialog.set_value("post_bonus_qty", 0);
    }
}

function update_holding_qty(dialog) {
    let script = dialog.get_value("script");
    let date = dialog.get_value("date");
    if (!script || !date) {
        dialog.set_value("holding_qty", 0);
        calculate_post_bonus_preview(dialog);
        return;
    }
    frappe.call({
        method:
            "portfolio.portfolio.doctype.investment_portfolio.investment_portfolio.get_holding_qty",
        args: { script: script, date: date },
        callback: function (r) {
            dialog.set_value("holding_qty", r.message || 0);
            calculate_post_bonus_preview(dialog);
        },
    });
}

function show_bonus_dialog(listview) {
	frappe.call({
		method:
			"portfolio.portfolio.doctype.investment_portfolio.investment_portfolio.get_bonus_scripts",
		freeze: true,
		callback: function (r) {
			let script_list = r.message || [];

			let dialog = new frappe.ui.Dialog({
				title: __("Apply Bonus"),
				fields: [
					{
						fieldname: "script",
						fieldtype: "Autocomplete",
						label: __("Script"),
						options: script_list,
						reqd: 1,
						onchange: function () {
							update_holding_qty(dialog);
						},
					},
					{
						fieldname: "date",
						fieldtype: "Date",
						label: __("Record Date"),
						default: frappe.datetime.get_today(),
						reqd: 1,
						onchange: function () {
							update_holding_qty(dialog);
						},
					},
					{
						fieldname: "holding_qty",
						fieldtype: "Float",
						label: __("Total Holding Qty"),
						read_only: 1,
					},
					{
						fieldname: "ratio",
						fieldtype: "Float",
						label: __("Bonus Ratio"),
						reqd: 1,
						onchange: function () {
							calculate_post_bonus_preview(dialog);
						},
					},
					{
						fieldname: "bonus_date",
						fieldtype: "Date",
						label: __("Bonus Date"),
						reqd: 1,
					},
					{
						fieldname: "post_bonus_qty",
						fieldtype: "Float",
						label: __("Post Bonus Qty"),
						read_only: 1,
					},
				],
				primary_action_label: __("Apply"),
				primary_action: function (values) {
					frappe.call({
						method:
							"portfolio.portfolio.doctype.investment_portfolio.investment_portfolio.apply_bonus",
						args: {
							script: values.script,
							ratio: values.ratio,
							bonus_date: values.bonus_date,
							date: values.date,
						},
						freeze: true,
						freeze_message: __("Applying Bonus..."),
						callback: function (r) {
							frappe.msgprint(
								__("Updated {0} document(s)", [(r.message || []).length])
							);
							dialog.hide();
							listview.refresh();
						},
					});
				},
			});
			dialog.show();
		},
	});
}

