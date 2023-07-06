frappe.ui.form.on('Journal Entry', {
onload: function(frm){
    frm.ignore_doctypes_on_cancel_all = ["Investment Portfolio"]; 
},
});