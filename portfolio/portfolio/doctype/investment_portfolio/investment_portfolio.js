// Copyright (c) 2023, finbyz and contributors
// For license information, please see license.txt
frappe.ui.form.on('Investment Portfolio', {
	total_value:function(frm){
		let total_price=frm.doc.qty*frm.doc.entry_price;
		cur_frm.set_value("entry_amount",total_price)
	},
	qty:function(frm){
		if(frm.doc.qty){
		frm.trigger("total_value")}
	},
	purchase_entry_price: function(frm) {
		if (frm.doc.purchase_entry_price && (!frm.doc.entry_price || flt(frm.doc.entry_price) === 0)) {
			frm.set_value("entry_price", frm.doc.purchase_entry_price);
		}
	},
	entry_price:function(frm){
		if (frm.doc.entry_price && (!frm.doc.purchase_entry_price || flt(frm.doc.purchase_entry_price) === 0)) {
			frm.set_value("purchase_entry_price", frm.doc.entry_price);
		}
		if(frm.doc.entry_price){
			frm.trigger("total_value")
		}
	},
	cal_entry_charges:function(frm){
		let entry_amount=frm.doc.entry_amount;
		let total_cost_of_ownership=frm.doc.total_cost_of_ownership;
		let total_entry_charges=flt(total_cost_of_ownership)-flt(entry_amount)
		cur_frm.set_value("entry_charges",total_entry_charges)

	},
	entry_charges: function(frm) {
		if (frm.doc.set_entry_charges_manually === 1) {
			frm.set_value('total_cost_of_ownership', frm.doc.entry_amount + frm.doc.entry_charges);
		}
	},
	set_entry_charges_manually:  function(frm) {
		if (frm.doc.set_entry_charges_manually === 1) {
			frm.set_df_property('entry_charges', 'read_only', 0);
		} else {
			frm.set_df_property('entry_charges', 'read_only', 1);
		}
	},
	cal_exit_charges:function(frm){
		let net=flt(frm.doc.exit_amount - frm.doc.net_exit_amount)
		frm.set_value("exit_charges",net)
		frm.refresh_field('exit_charges')

	},
	set_charges:function(frm){
		if(frm.doc.set_charges==1){
			frm.trigger("cal_exit_charges")
		}
	},
	exit_price:function(frm){
		if(frm.doc.exit_price ){
			frm.trigger("cal_exit_charges")
		}
		if(frm.doc.entry_price){
		frm.trigger("total_values")
		frm.trigger('cal_exit_charges')
		}
	},
	exit_qty:function(frm){
		if(frm.doc.exit_price ){
			frm.trigger("cal_exit_charges")
		}
		if(frm.doc.exit_qty){
			frm.trigger("total_values")}
	},

	post_split_qty: function(frm) {
		render_split_summary(frm);
	},

	split: function(frm) {
		let post_split_qty = flt(frm.doc.post_split_qty);
		if (!post_split_qty || post_split_qty <= 0) {
			frappe.msgprint({
				title: __("Validation"),
				indicator: "red",
				message: __("Please enter a valid <strong>Qty After Split</strong> first.")
			});
			return;
		}

		let split_rows = frm.doc.investment_portfolio_split || [];
		if (!split_rows.length) {
			frappe.msgprint({
				title: __("Validation"),
				indicator: "red",
				message: __("Please add at least one row in the <strong>Investment Portfolio Split</strong> table.")
			});
			return;
		}

		let base_qty = (frm.doc.pending_qty !== undefined && frm.doc.pending_qty !== null && flt(frm.doc.pending_qty) > 0)
			? flt(frm.doc.pending_qty)
			: flt(frm.doc.qty);
		let target_amount = base_qty * flt(frm.doc.entry_price);
		let total_split_amount = 0.0;
		let total_split_qty = 0.0;

		for (let row of split_rows) {
			if (!row.script || !flt(row.qty) || !flt(row.per_share_price)) {
				frappe.msgprint({
					title: __("Validation"),
					indicator: "red",
					message: __("Row {0}: Script, Qty and Per Share Price are all required.", [row.idx])
				});
				return;
			}
			row.amount = flt(row.qty) * flt(row.per_share_price);
			total_split_amount += row.amount;
			total_split_qty += flt(row.qty);
		}

		let currency = frm.doc.currency || "INR";
		let diff_amount = target_amount - total_split_amount;
		let diff_qty = post_split_qty - total_split_qty;

		if (Math.abs(diff_qty) > 0.0001) {
			frappe.msgprint({
				title: __("Qty Mismatch"),
				indicator: "red",
				message: __("Total Split Qty (<strong>{0}</strong>) must equal Qty After Split (<strong>{1}</strong>).<br>Difference: <strong>{2}</strong>", [
					format_number(total_split_qty, null, 4),
					format_number(post_split_qty, null, 4),
					format_number(diff_qty, null, 4)
				])
			});
			return;
		}

		if (Math.abs(diff_amount) > 0.01) {
			let msg = diff_amount > 0
				? __("Total Split Amount (<strong>{0}</strong>) is less than Required Amount (<strong>{1}</strong> = {2} Pending Qty × {3}).<br>Additional Amount Needed: <strong style='color:red;'>{4}</strong>", [
					format_currency(total_split_amount, currency),
					format_currency(target_amount, currency),
					format_number(base_qty, null, 4),
					format_currency(frm.doc.entry_price, currency),
					format_currency(diff_amount, currency)
				])
				: __("Total Split Amount (<strong>{0}</strong>) exceeds Required Amount (<strong>{1}</strong> = {2} Pending Qty × {3}) by <strong style='color:red;'>{4}</strong>.", [
					format_currency(total_split_amount, currency),
					format_currency(target_amount, currency),
					format_number(base_qty, null, 4),
					format_currency(frm.doc.entry_price, currency),
					format_currency(Math.abs(diff_amount), currency)
				]);
			frappe.msgprint({
				title: __("Amount Mismatch"),
				indicator: "red",
				message: msg
			});
			return;
		}

		frappe.confirm(
			__("This will mark the document as Exited and create new Investment Portfolio document(s) for each row. Continue?"),
			function() {
				frappe.call({
					method: "portfolio.portfolio.doctype.investment_portfolio.investment_portfolio.process_split",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Processing Split..."),
					callback: function(r) {
						if (r.message) {
							frappe.msgprint(
								__("Created: {0}", [r.message.map(d => frappe.utils.get_form_link("Investment Portfolio", d, true)).join(", ")])
							);
						}
						frm.reload_doc();
					}
				});
			}
		);
	},

	onload:function(frm){
		if(frm.doc.docstatus == 0 && frm.doc.is_existing == 0){
			frm.set_value("jv_of_entry","")
			frm.set_value("jv_of_exit","")
		}
		if(frm.doc.is_existing == 1 && frm.doc.docstatus == 0 ) {
			frm.set_df_property('jv_of_entry', 'read_only', 0);
		}
		// else if(frm.doc.docstatus==1){
		// 	frm.set_df_property('qty', 'read_only', 1);
		// 	frm.set_df_property('entry_price', 'read_only', 1);
		// 	frm.set_df_property('holding_account', 'read_only', 1);
		// 	frm.set_df_property('entry_amount', 'read_only', 1);
		// 	frm.set_df_property('total_cost_of_ownership', 'read_only', 1);
		// 	frm.set_df_property('entry_charges', 'read_only', 1);
		// 	frm.set_df_property('funds_debited_from', 'read_only', 1);
		// 	frm.set_df_property('investment_charges_account', 'read_only', 1);

		// }
		else{
			frm.set_df_property('jv_of_entry', 'read_only', 1);
		}
	},
	is_existing:function(frm){
		if(frm.doc.is_existing == 1 && frm.doc.docstatus == 0 ) {
			frm.set_df_property('jv_of_entry', 'read_only', 0);
			frm.set_query('jv_of_entry', function(doc) {
				return {
					filters: {
						"docstatus": 1
					}
				};
			});
		} else {
			frm.set_df_property('jv_of_entry', 'read_only', 1);
		}
	},
	refresh:function(frm){
		if (frm.doc.__islocal) {
			frappe.db.get_value("Company", {"name": frm.doc.company}, ['bank_account', 'capital_account', 'investment_charges_account'],
			function(value) {
				frm.set_value('funds_debited_from', value.bank_account);
				frm.set_value('holding_account', value.capital_account);
				frm.set_value('investment_charges_account', value.investment_charges_account);
			});
		}
		if (frm.doc.docstatus === 1) {
			frappe.db.get_value("Company", {"name": frm.doc.company}, ['bank_account', 'investment_income_account'], 
			function(value) {
				if (!frm.doc.bank_account) {
					frm.doc.bank_account = value.bank_account;
					frm.refresh_field('bank_account');
				}
				if (!frm.doc.funds_credited_to) {
					frm.doc.funds_credited_to = value.investment_income_account;
					frm.refresh_field('funds_credited_to');
				}
			});
		}
		frm.set_query("holding_account", function(doc) {
			return {
				"filters": {
					"company": doc.company,
					"root_type":"Asset",
					"is_group": 0
					
				}
			};
		});
		frm.set_query('funds_debited_from', function(doc) {
			return {
				filters: {
					"is_group": 0,
					"company": doc.company,
					"account_type": "Bank"
				
				}
			};
		});
		frm.set_query('investment_charges_account', function(doc) {
			return {
				filters: {
					"is_group": 0,
					"company": doc.company,
					"account_type":"Expense Account"
				
				}
			};
		});
		frm.set_query('bank_account', function(doc) {
			return {
				filters: {
					"is_group": 0,
					"company": doc.company,
					"account_type": "Bank"
				
				}
			};
		});
		frm.set_query('funds_credited_to', function(doc) {
			return {
				filters: {
					"is_group": 0,
					"company": doc.company,
					"account_type":"Income Account"
				
				}
			};
		});
		render_split_summary(frm);
	},
	validate: function(frm) {
		if (frm.doc.total_cost_of_ownership < frm.doc.entry_amount) {
			frappe.throw("Total Cost of Ownership should be greater than or greater than equal to Entry Amount.");
			validated = false;
		}
	},
	net_exit_amount:function(frm){
		frm.trigger("cal_exit_charges")
	},
	exit_charges:function(frm) {
		if (frm.doc.set_charges==1) {
			frm.set_value('net_exit_amount', frm.doc.exit_amount - frm.doc.exit_charges);
		}
	},
	total_values:function(frm){
		let total_prices=frm.doc.exit_qty*frm.doc.exit_price;
	
		cur_frm.set_value("exit_amount",total_prices);
		cur_frm.set_value("net_exit_amount",total_prices)
		},

	
	entry_amount:function(frm){
		frm.trigger("cal_entry_charges")
	},
	// exit_amount:function(frm){
	// 	frm.trigger("cal_exit_charges")
	// },

	total_cost_of_ownership:function(frm){
		frm.trigger("cal_entry_charges")
	},

	create_exit_jv:function(frm){
		if (frm.doc.__unsaved){
			frappe.throw("Please First Save Document")
		}
		frappe.call({
			method: "portfolio.portfolio.doctype.investment_portfolio.investment_portfolio.create_exit",
            args: {
                    "exit_price": frm.doc.exit_price,
					"exit_qty": frm.doc.exit_qty,
					"exit_date": frm.doc.exit_date,
					"exit_amount": frm.doc.exit_amount,
					"net_exit_amount": frm.doc.net_exit_amount,
					"jv_of_exit":frm.doc.jv_of_exit,
					"name":frm.doc.name
                },
				callback: function (r) {
					cur_frm.refresh_field('investment_portfolio_segment');
					frappe.ui.toolbar.clear_cache();
				}
			});
		}
});


frappe.ui.form.on('Investment Portfolio Split', {
    qty: function(frm, cdt, cdn) {
        calculate_split_row_amount(frm, cdt, cdn);
        render_split_summary(frm);
    },
    per_share_price: function(frm, cdt, cdn) {
        calculate_split_row_amount(frm, cdt, cdn);
        render_split_summary(frm);
    },
    investment_portfolio_split_remove: function(frm) {
        render_split_summary(frm);
    },
    investment_portfolio_split_add: function(frm) {
        render_split_summary(frm);
    }
});

function calculate_split_row_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.qty) * flt(row.per_share_price);
    frm.refresh_field("investment_portfolio_split");
}

function render_split_summary(frm) {
    if (!frm.fields_dict.split_summary_html || !frm.fields_dict.split_summary_html.$wrapper) return;

    let post_split_qty = flt(frm.doc.post_split_qty);
    let entry_price = flt(frm.doc.entry_price);
    let base_qty = (frm.doc.pending_qty !== undefined && frm.doc.pending_qty !== null && flt(frm.doc.pending_qty) > 0)
        ? flt(frm.doc.pending_qty)
        : flt(frm.doc.qty);
    let target_amount = base_qty * entry_price;

    let total_split_qty = 0.0;
    let total_split_amount = 0.0;

    (frm.doc.investment_portfolio_split || []).forEach(row => {
        let q = flt(row.qty);
        let p = flt(row.per_share_price);
        row.amount = q * p;
        total_split_qty += q;
        total_split_amount += row.amount;
    });

    let diff_qty = post_split_qty - total_split_qty;
    let diff_amount = target_amount - total_split_amount;

    let currency = frm.doc.currency || "INR";
    let is_amount_matched = Math.abs(diff_amount) < 0.01 && target_amount > 0;
    let is_qty_matched = Math.abs(diff_qty) < 0.0001 && post_split_qty > 0;

    let status_badge = "";
    if (post_split_qty <= 0) {
        status_badge = `<span class="indicator-pill orange">${__("Please enter Qty After Split")}</span>`;
    } else if (is_amount_matched && is_qty_matched) {
        status_badge = `<span class="indicator-pill green"><strong>${__("✓ Amount & Qty Matched")}</strong></span>`;
    } else {
        let msgs = [];
        if (!is_qty_matched) {
            msgs.push(diff_qty > 0 ? `${__("Need Qty")}: ${format_number(diff_qty, null, 4)}` : `${__("Excess Qty")}: ${format_number(Math.abs(diff_qty), null, 4)}`);
        }
        if (!is_amount_matched) {
            msgs.push(diff_amount > 0 ? `${__("Need Amount")}: ${format_currency(diff_amount, currency)}` : `${__("Excess Amount")}: ${format_currency(Math.abs(diff_amount), currency)}`);
        }
        status_badge = `<span class="indicator-pill red"><strong>${msgs.join(" | ")}</strong></span>`;
    }

    let html = `
        <div style="margin-top: 10px; margin-bottom: 15px; padding: 14px; background-color: var(--bg-light-gray, #f8f9fa); border: 1px solid var(--border-color, #d1d8dd); border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h6 style="margin: 0; font-weight: 600; color: var(--text-color);">${__("Split Calculation & Validation Summary")}</h6>
                <div>${status_badge}</div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
                <div style="padding: 10px; background: var(--card-bg, #ffffff); border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0);">
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">${__("Required Split Amount")}</div>
                    <div style="font-size: 15px; font-weight: bold; color: var(--text-color); margin-top: 4px;">${format_currency(target_amount, currency)}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">${format_number(base_qty, null, 4)} (Pending Qty) × ${format_currency(entry_price, currency)}</div>
                </div>
                <div style="padding: 10px; background: var(--card-bg, #ffffff); border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0);">
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">${__("Total Entered Amount")}</div>
                    <div style="font-size: 15px; font-weight: bold; color: ${is_amount_matched ? 'var(--green-600, #28a745)' : 'var(--red-600, #e02424)'}; margin-top: 4px;">${format_currency(total_split_amount, currency)}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">${__("Sum of rows in child table")}</div>
                </div>
                <div style="padding: 10px; background: var(--card-bg, #ffffff); border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0);">
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">${__("Amount Remaining / Needed")}</div>
                    <div style="font-size: 15px; font-weight: bold; color: ${is_amount_matched ? 'var(--green-600, #28a745)' : 'var(--red-600, #e02424)'}; margin-top: 4px;">${format_currency(diff_amount, currency)}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">${is_amount_matched ? __('Exact match') : (diff_amount > 0 ? __('Shortage') : __('Excess'))}</div>
                </div>
                <div style="padding: 10px; background: var(--card-bg, #ffffff); border-radius: 6px; border: 1px solid var(--border-color, #e2e8f0);">
                    <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">${__("Qty (Entered / Target)")}</div>
                    <div style="font-size: 15px; font-weight: bold; color: ${is_qty_matched ? 'var(--green-600, #28a745)' : 'var(--red-600, #e02424)'}; margin-top: 4px;">${format_number(total_split_qty, null, 4)} / ${format_number(post_split_qty, null, 4)}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">${is_qty_matched ? __('Qty matched') : `${__('Difference')}: ${format_number(diff_qty, null, 4)}`}</div>
                </div>
            </div>
        </div>
    `;

    frm.fields_dict.split_summary_html.$wrapper.html(html);
}






