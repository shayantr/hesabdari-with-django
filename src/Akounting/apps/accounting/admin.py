from django.contrib import admin
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from Akounting.apps.accounting.models.accounts import AccountsClass
from Akounting.apps.accounting.models.balancesheet import BalanceSheet
from Akounting.apps.accounting.models.cheque import CashierCheque
from Akounting.apps.accounting.models.document import Document


# Register your models here.

class AccountsAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title', 'name', 'parent')



class AccountsClassAdmin(TreeAdmin):
    form = movenodeform_factory(AccountsClass)  # امکان جابجایی درختی

# admin.site.register(AccountsClass, AccountsClassAdmin)
admin.site.register(AccountsClass)

admin.site.register(CashierCheque)
admin.site.register(BalanceSheet)
admin.site.register(Document)
