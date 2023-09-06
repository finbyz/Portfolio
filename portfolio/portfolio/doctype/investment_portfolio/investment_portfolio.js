// Copyright (c) 2023, finbyz and contributors
// For license information, please see license.txt
frappe.ui.form.on('Investment Portfolio', {
	total_value:function(frm){
		if(!frm.doc.manual_entry_amount){
         let total_price=frm.doc.qty*frm.doc.entry_price;
		 cur_frm.set_value("entry_amount",total_price)
		}
	},
	qty:function(frm){
		if(frm.doc.qty){
		frm.trigger("total_value")}
	},
	entry_price:function(frm){
		if(frm.doc.entry_price){
		frm.trigger("total_value")
	}},
	manual_entry_amount:function(frm){
		if(frm.doc.entry_price && frm.doc.qty && frm.doc.manual_entry_amount ==0){
		frm.trigger("total_value")
	}},	
	cal_entry_charges:function(frm){
		let entry_amount=frm.doc.entry_amount;
		let total_cost_of_ownership=frm.doc.total_cost_of_ownership;
		let total_entry_charges=flt(total_cost_of_ownership)-flt(entry_amount)
		cur_frm.set_value("entry_charges",total_entry_charges)

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


		






