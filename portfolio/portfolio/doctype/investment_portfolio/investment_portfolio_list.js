let imports_in_progress = [];

frappe.listview_settings['Investment Portfolio'] = {
	add_fields: ['status','qty','total_cancelled'],
	get_indicator: function(doc) {
        
	    if(doc.total_cancelled==0.0){
            return [__("holding"), "orange", "status,=,holding"];
        }
        if(doc.qty==doc.total_cancelled){
            return [__("Exited"), "red", "status,=,Exited"];
      }
		
		if(parseFloat((doc.qty)/2)<=doc.total_cancelled){
            return [__("Partially Exited"), "gray", "status,=,Partially Exited"];
        }
       
	},
   
	hide_name_column: true
};
