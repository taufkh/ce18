{
    'name': 'TH Currency Rate Request',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Request and update currency rate by date from external API',
    'author': 'Taufik',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/currency_rate_update_wizard_views.xml',
        'views/res_currency_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
