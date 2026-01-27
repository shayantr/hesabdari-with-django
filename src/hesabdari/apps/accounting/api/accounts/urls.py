from django.urls import path

from hesabdari.apps.accounting.api.accounts.views import accouns_manager, UpdateBulkAccount, delete_account, \
    edit_account, create_accounts, AccountsView

urlpatterns = [
    path('items/accounts-list/', AccountsView.as_view(), name='get_accounts_list'),
    path('items/accounts-list/create', create_accounts, name='create_accounts'),
    path('accounts/edit/<int:pk>/', edit_account, name='edit_account'),
    path('accounts/delete/<int:pk>/', delete_account, name='delete_account'),
    path('transfer-accounts/', UpdateBulkAccount.as_view(), name='transfer-accounts'),
    path('accounts-manager/', accouns_manager, name='accounts_manager'),

]