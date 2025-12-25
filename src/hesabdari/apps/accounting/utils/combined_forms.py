from collections import namedtuple

CombinedForm = namedtuple(
    'CombinedForm',
    ['uniqueid', 'form_balance', 'form_cheque', 'chequeid', 'account_str', 'bank_str', 'balance_id', 'is_active']
)

PostCombinedForm = namedtuple(
    'PostCombinedForm',
    ['uniqueid', 'form_balance', 'form_cheque']
)