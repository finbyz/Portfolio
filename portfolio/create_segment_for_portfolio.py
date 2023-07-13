import frappe

def after_install():
    ivs=frappe.new_doc("Investment Segment")
    ivs.segment="Mutual Funds"
    ivs.save()

    ivs=frappe.new_doc("Investment Segment")
    ivs.segment="Equity"
    ivs.save()
 

    cat=frappe.new_doc("Category")
    cat.category="Debt"
    cat.save()
    
    cat=frappe.new_doc("Category")
    cat.category="Equity"
    cat.save()
   