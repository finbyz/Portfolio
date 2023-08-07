# Copyright (c) 2023, finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, date_diff, nowdate, get_url_to_form,flt
import erpnext

class InvestmentPortfolio(Document):
	
	def validate(self):
		self.calculate_entry_amount()
		self.calculate_pending_qty()
		
	def on_update_after_submit(self):
		self.calculate_pending_qty()
		self.set_status()

	def on_cancel(self):
		self.set_status()
		self.cancel_jv()
	

	def on_update(self):
		self.set_status()
		if self.docstatus == 0 and self.is_existing == 0:
			self.jv_of_entry = None
			self.jv_of_exit = None


	def set_status(self):
		if self.docstatus == 0:
			self.status = "Draft"
		if self.docstatus == 1:
			print(self.pending_qty)
			print(self.qty)
			if self.pending_qty==self.qty:
				self.status="Holding"
			if self.qty!=self.pending_qty:
				self.status="Partially Exited"
			if self.pending_qty == 0:
				self.status="Exited"
		if self.docstatus ==2:
			self.status = "Cancelled"
		
		
	def on_submit(self):
		self.set_status()
		if not self.jv_of_entry:
			self.create_row_entry_jv()	
		
	def calculate_entry_amount(self):
		if not self.manual_entry_amount:
			self.entry_amount=self.qty*self.entry_price
	
	def calculate_exit_amount(self):
		self.exit_amount=self.exit_price*self.exit_qty
		
	def validate_exit_date(self):
		if self.posting_date > self.exit_date:
			frappe.throw("Exit Date Cannot be Greater than Investment Date")	
	
	def create_row_exit_jv(self):
		if not self.bank_account:
			frappe.throw("Bank Account is compulsory")
		if self.net_exit_amount > self.exit_amount:
			frappe.throw("Net Exit Amount Should not be Greater than Exit Amount")
		
		cost_center = erpnext.get_default_cost_center(self.company)
		if not self.set_charges==1:
			jv = frappe.new_doc("Journal Entry")
			jv.voucher_type = "Journal Entry"
			jv.posting_date = self.exit_date
			net= (self.net_exit_amount - (self.exit_qty*self.entry_price))
			if not self.company:
				self.db_set('company', frappe.defaults.get_global_default('company'))

			jv.company = self.company

			
			jv.append('accounts', {
				'account': self.bank_account,
				'debit_in_account_currency': self.net_exit_amount,
				'cost_center':cost_center,
			})

			jv.append('accounts', {
				'account': self.holding_account,
				'credit_in_account_currency': (self.exit_qty*self.entry_price),
				'cost_center':cost_center,
			})
			jv.append('accounts', {
				'account': self.funds_credited_to,
				'credit_in_account_currency': net,
				'cost_center':cost_center,
			})

			jv.cheque_no = self.name
			jv.cheque_date = self.exit_date
			

			try:
				jv.save()
				jv.submit()
				self.jv_of_exit = jv.name
				url = get_url_to_form("Journal Entry", jv.name)
				frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))
				return jv.name
			except Exception as e:
				frappe.throw(_(str(e)))	
		else:
			jv = frappe.new_doc("Journal Entry")
			jv.voucher_type = "Journal Entry"
			jv.posting_date = self.exit_date
			net= (self.net_exit_amount - (self.exit_qty*self.entry_price))
			if not self.company:
				self.db_set('company', frappe.defaults.get_global_default('company'))

			jv.company = self.company
			calculated_exit_amount=self.exit_qty*self.entry_price
			if self.exit_amount > calculated_exit_amount:
				jv.append('accounts', {
					'account': self.bank_account,
					'debit_in_account_currency': self.net_exit_amount,
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.investment_charges_account,
					'debit_in_account_currency': self.exit_charges,
					'cost_center':cost_center,
				})

				jv.append('accounts', {
					'account': self.holding_account,
					'credit_in_account_currency': (self.exit_qty*self.entry_price),
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.funds_credited_to,
					'credit_in_account_currency': (self.exit_amount-s),
					'cost_center':cost_center,
				})
			elif  self.exit_amount < calculated_exit_amount:
				jv.append('accounts', {
					'account': self.bank_account,
					'debit_in_account_currency': self.net_exit_amount,
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.investment_charges_account,
					'debit_in_account_currency': self.exit_charges,
					'cost_center':cost_center,
				})
				exit_amount_with_charges=self.net_exit_amount+ self.exit_charges
				jv.append('accounts', {
					'account': self.funds_credited_to,
					'debit_in_account_currency': (calculated_exit_amount-exit_amount_with_charges),
					'cost_center':cost_center,
				})

				jv.append('accounts', {
					'account': self.holding_account,
					'credit_in_account_currency': (self.exit_qty*self.entry_price),
					'cost_center':cost_center,
				})
			elif self.exit_amount == calculated_exit_amount:
				jv.append('accounts', {
					'account': self.bank_account,
					'debit_in_account_currency': self.net_exit_amount,
					'cost_center':cost_center,
				})
				jv.append('accounts', {
					'account': self.investment_charges_account,
					'debit_in_account_currency': self.exit_charges,
					'cost_center':cost_center,
				})
				# v=self.net_exit_amount+ self.exit_charges
				# jv.append('accounts', {
				# 	'account': self.funds_credited_to,
				# 	'debit_in_account_currency': (s-v)
				# })

				jv.append('accounts', {
					'account': self.holding_account,
					'credit_in_account_currency': (self.exit_amount),
					'cost_center':cost_center,
				})


			jv.cheque_no = self.name
			jv.cheque_date = self.exit_date
			

			try:
				jv.save()
				jv.submit()
				self.jv_of_exit = jv.name
				url = get_url_to_form("Journal Entry", jv.name)
				frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))
				return jv.name
			except Exception as e:
				frappe.throw(_(str(e)))


	def create_row_entry_jv(self):		
		jv = frappe.new_doc("Journal Entry")
		jv.voucher_type = "Journal Entry"
		jv.posting_date = self.posting_date
		
		if not self.company:
			self.db_set('company', frappe.defaults.get_global_default('company'))

		jv.company = self.company
		cost_center = erpnext.get_default_cost_center(self.company)

		
		jv.append('accounts', {
			'account': self.funds_debited_from,
			'credit_in_account_currency': self.total_cost_of_ownership,
			'cost_center': cost_center
		})
		if self.entry_charges != 0:
			jv.append('accounts', {
				'account': self.investment_charges_account,
				'debit_in_account_currency': self.entry_charges,
				'cost_center': cost_center
			})
		jv.append('accounts', {
			'account': self.holding_account,
			'debit_in_account_currency': self.entry_amount,
			'cost_center': cost_center
		})

		jv.cheque_no = self.name
		jv.cheque_date = self.posting_date

		try:
			print(jv.accounts[0].cost_center)
			jv.save()
			print(jv.accounts[0].cost_center)
			jv.submit()
			self.db_set("jv_of_entry" , jv.name)
		except Exception as e:
			frappe.throw(_(str(e)))
		else:
			
			url = get_url_to_form("Journal Entry", jv.name)
			frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been created.".format(url=url, doc=frappe.bold(jv.name))))

	def calculate_pending_qty(self):
		if not self.exit_qty and not len(self.investment_portfolio_segment):
			self.pending_qty=self.qty
		else:
			total=0
			for row1 in self.investment_portfolio_segment:
				total+=flt(row1.exit_qty)
			self.pending_qty=self.qty-total

	def cancel_jv(self):
		if self.jv_of_entry:
			jv = frappe.get_doc("Journal Entry",self.jv_of_entry)
			jv.cancel()
			url = get_url_to_form("Journal Entry", jv.name)
			frappe.msgprint(_("Journal Entry - <a href='{url}'>{doc}</a> has been cancelled .".format(url=url, doc=frappe.bold(jv.name))))	
		for row in self.investment_portfolio_segment:
			jv_doc = frappe.get_doc("Journal Entry" , row.jv_of_exit)
			jv_doc.cancel()

@frappe.whitelist()
def create_exit(exit_price ,exit_qty , exit_date , exit_amount ,net_exit_amount , name ,jv_of_exit = None):
	doc = frappe.get_doc("Investment Portfolio" , name)
	doc.calculate_exit_amount()
	jv = doc.create_row_exit_jv()
	doc.append("investment_portfolio_segment" , {"exit_price":exit_price,"exit_date":exit_date ,"exit_qty":exit_qty , "exit_amount":exit_amount , "net_exit_amount" : net_exit_amount,"jv_of_exit": jv})
	if sum([flt(row.exit_qty) for row in doc.investment_portfolio_segment]) > flt(doc.qty):
		frappe.throw("Exit Quantity should not be greater than quantity")
	doc.calculate_pending_qty()
	doc.exit_price=0
	doc.exit_qty=0
	doc.exit_amount=0
	doc.net_exit_amount=0
	doc.save()	