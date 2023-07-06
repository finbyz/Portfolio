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
	entry_price:function(frm){
		if(frm.doc.entry_price){
		frm.trigger("total_value")
	}},
	cal_entry_charges:function(frm){
		let entry_amount=frm.doc.entry_amount;
		let total_cost_of_ownership=frm.doc.total_cost_of_ownership;
		let total_entry_charges=flt(total_cost_of_ownership)-flt(entry_amount)
		console.log(total_entry_charges)
		cur_frm.set_value("entry_charges",total_entry_charges)

	},
	// cal_exit_charges:function(frm){
	// 	let entry_amount=frm.doc.entry_amount;
	// 	let exit_amount=frm.doc.exit_amount;
	// 	let net=flt(entry_amount)-flt(exit_amount)
	// 	console.log(net)
	// 	cur_frm.set_value("net_exit_amount",net)

	// },
	
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

	total_values:function(frm){
	let total_prices=frm.doc.exit_qty*frm.doc.exit_price;
   
	cur_frm.set_value("exit_amount",total_prices)
	},
	exit_qty:function(frm){
   	if(frm.doc.exit_qty){
   	frm.trigger("total_values")}
	},
	exit_price:function(frm){
   	if(frm.doc.entry_price){
   	frm.trigger("total_values")
	}},

	
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
	

	// cal_exit_charges_calculated:function(frm,cdt,cdn){
    //     let d = locals[cdt][cdn]
	// 	cur_frm.set_value(cdt,cdn,"exit_charges_calculated",frm.doc.net_exit_amount-d.exit_amount)
	// },
	// cal_difference_rate:function(frm,cdt,cdn){
	// 	let enter_price=frm.doc.entry_price
	// 	let exit_price=frm.doc.exit_price
	// 	console.log(enter_price)
	// 	console.log(exit_price)
	// 	frappe.model.set_value(cdt,cdn,"rate_diff",exit_price-enter_price)


	// }
});


		






