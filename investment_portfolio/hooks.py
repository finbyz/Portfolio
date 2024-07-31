from . import __version__ as app_version

app_name = "investment_portfolio"
app_title = "Investment Portfolio"
app_publisher = "FinByz"
app_description = "Investment Portfolio"
app_email = "info.finbyz.com"
app_license = "MIT"

# Includes in <head>
# ------------------

fixtures = [{
    "doctype": "Custom Field",
        "filters": {
            "module": ["in", ["Investment Portfolio"]]
            }
    }
]


# include js, css files in header of desk.html
# app_include_css = "/assets/investment_portfolio/css/investment_portfolio.css"
# app_include_js = "/assets/investment_portfolio/js/investment_portfolio.js"

# include js, css files in header of web template
# web_include_css = "/assets/investment_portfolio/css/investment_portfolio.css"
# web_include_js = "/assets/investment_portfolio/js/investment_portfolio.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "investment_portfolio/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}
doctype_js = {
	"Journal Entry" : "public/js/journal_entry.js",
	"Company" : "public/js/company.js"
	}
# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "investment_portfolio.utils.jinja_methods",
#	"filters": "investment_portfolio.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "investment_portfolio.install.before_install"
# after_install = "investment_portfolio.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "investment_portfolio.uninstall.before_uninstall"
after_install = "investment_portfolio.create_doc.create_document.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "investment_portfolio.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Journal Entry": {
		"before_cancel": "investment_portfolio.investment_portfolio.doctype.journal_entry.on_cancel"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"investment_portfolio.tasks.all"
#	],
#	"daily": [
#		"investment_portfolio.tasks.daily"
#	],
#	"hourly": [
#		"investment_portfolio.tasks.hourly"
#	],
#	"weekly": [
#		"investment_portfolio.tasks.weekly"
#	],
#	"monthly": [
#		"investment_portfolio.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "investment_portfolio.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "investment_portfolio.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "investment_portfolio.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["investment_portfolio.utils.before_request"]
# after_request = ["investment_portfolio.utils.after_request"]

# Job Events
# ----------
# before_job = ["investment_portfolio.utils.before_job"]
# after_job = ["investment_portfolio.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"investment_portfolio.auth.validate"
# ]
