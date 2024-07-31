import frappe
def after_install():
    create_document()
def execute():
    create_document()
    
def create_document():
    if not frappe.db.exists("Investment Segment" , "Mutual Funds"):
        ivs=frappe.new_doc("Investment Segment")
        ivs.segment="Mutual Funds"
        ivs.save()
    if not frappe.db.exists("Investment Segment" , "ETF"):
        ivs=frappe.new_doc("Investment Segment")
        ivs.segment="ETF"
        ivs.save()
    if not frappe.db.exists("Investment Segment" , "Equity"):
        ivs=frappe.new_doc("Investment Segment")
        ivs.segment="Equity"
        ivs.save()
 
    if not frappe.db.exists("Category" , "Debt"):
        cat=frappe.new_doc("Category")
        cat.category="Debt"
        cat.save()
    
    if not frappe.db.exists("Category" , "Equity"):
        cat=frappe.new_doc("Category")
        cat.category="Equity"
        cat.save()