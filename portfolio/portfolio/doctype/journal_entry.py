import frappe
from frappe.utils import flt, cint, get_url_to_form
from frappe import _
def on_cancel(self,method):
    if frappe.db.exists("Investment Portfolio Segment" , {'jv_of_exit' : self.name}):
        ips, parent = frappe.db.get_value("Investment Portfolio Segment", {'jv_of_exit' : self.name}, ["name", 'parent'])
        if ips and parent:
            frappe.db.sql(f"""DELETE FROM `tabInvestment Portfolio Segment` 
            WHERE name = '{ips}'""")
    total = 0
    parent_doc =  frappe.get_doc("Investment Portfolio" , parent )
    for row in parent_doc.investment_portfolio_segment:
        total += row.get("exit_qty")

    parent_doc.db_set("pending_qty" , parent_doc.qty - total)
   
    if frappe.db.exists("Investment Portfolio",self.cheque_no):
        
        doc= frappe.get_doc("Investment Portfolio",self.cheque_no)
        if doc.jv_of_entry == self.name:
            doc.jv_of_entry = None
            doc.save
            if doc.docstatus == 1:
                doc.cancel()
    
            url = get_url_to_form("Journal Entry", doc.name)
            frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been cancelled .".format(url=url, doc=frappe.bold(doc.name))))

   
    

       
    







  