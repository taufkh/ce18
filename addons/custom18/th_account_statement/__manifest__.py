{
    'name': 'TH Account Statement',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Customer & Vendor Account Statement with Email & PDF Export',
    'description': """
        Generate and send account statements for customers and vendors.

        Features:
        - Customer Account Statement
        - Customer Overdue Statement
        - Vendor Account Statement
        - Vendor Overdue Statement
        - Export as PDF
        - Send via Email with PDF attachment
        - Ageing Summary (0-30, 31-60, 61-90, 91+ days)
        - Statement Log History
    """,
    'author': 'Taufik',
    'application': True,
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_statement_log_views.xml',
        'wizard/account_statement_wizard_views.xml',
        'report/account_statement_report.xml',
        'report/account_statement_templates.xml',
        'views/account_statement_menu.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
