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
	calculate_inramt: function(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		let inramt = flt(d.qty) * flt(d.rate);
		console.log(inramt)
		frappe.model.set_value(cdt, cdn, "exit_amount", inramt);
	},
	cal_calcellation_details: function(frm){
		let total = 0.0;
		let exit_total = 0.0;
		
		frm.doc.investment_portfolio_cancellation.forEach(function(d) {
			total += flt(d.qty);
			exit_total += flt(d.exit_amount);
		});
		frm.set_value("total_cancelled", total);
		frm.set_value("avg_exit_rate", exit_total/total);
		
	},
	cal_entry_charges:function(frm){
		let entry_amount=frm.doc.entry_amount;
		let total_cost_of_ownership=frm.doc.total_cost_of_ownership;
		let total_entry_charges=flt(total_cost_of_ownership)-flt(entry_amount)
		console.log(total_entry_charges)
		cur_frm.set_value("entry_charges",total_entry_charges)

	},
	refresh:function(frm){
	frm.set_query("holding_account", function(doc) {
		return {
			"filters": {
				"company": doc.company,
				"root_type":"Asset"
				
			}
		};
	})},
	entry_amount:function(frm){
		frm.trigger("cal_entry_charges")
	},
	total_cost_of_ownership:function(frm){
		frm.trigger("cal_entry_charges")
	},
	cal_exit_charges_calculated:function(frm,cdt,cdn){
        let d = locals[cdt][cdn]
		cur_frm.set_value(cdt,cdn,"exit_charges_calculated",frm.doc.net_exit_amount-d.exit_amount)
	},
	cal_difference_rate:function(frm,cdt,cdn){
		let enter_price=frm.doc.entry_price
		let exit_price=frm.doc.exit_price
		console.log(enter_price)
		console.log(exit_price)
		frappe.model.set_value(cdt,cdn,"rate_diff",exit_price-enter_price)


	}
});

frappe.ui.form.on("Investment Portfolio Cancellation", {
	
	
	qty: function(frm, cdt, cdn){		
		frm.events.cal_calcellation_details(frm);
		frm.events.calculate_inramt(frm, cdt, cdn);
	},
	
	rate: function(frm, cdt, cdn){
		frm.events.calculate_inramt(frm, cdt, cdn);
		
	}, 
	total_cost_of_ownership:function(frm){
		frm.events.cal_entry_charges(frm)
	},
	
	exit_amount: function(frm, cdt, cdn){
		frm.events.cal_calcellation_details(frm);
		frm.events.cal_exit_charges_calculated(frm);
		
	},
	create_jv: function(frm, cdt, cdn){
		const d = locals[cdt][cdn];
		frappe.call({
			method: 'create_jv',
			doc: frm.doc,
			args: {
				row: d.name
			},
			callback: function(r){
				if(!r.exc){
					frm.reload_doc();
				}
			}
		})
	},
	cancel_jv: function(frm, cdt, cdn){
		const d = locals[cdt][cdn];
		frappe.call({
			method: 'cancel_jv',
			doc: frm.doc,
			args: {
				row: d.name
			},
			callback: function(r){
				if(!r.exc){
					frm.reload_doc();
				}
			}
		})
	},
	
});