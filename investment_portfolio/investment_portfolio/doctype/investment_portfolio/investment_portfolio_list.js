let imports_in_progress = [];

frappe.listview_settings['Investment Portfolio'] = {
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
   
	// hide_name_column: true
};
