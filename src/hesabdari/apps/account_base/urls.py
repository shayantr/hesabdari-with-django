from django.urls import path, include

from hesabdari.apps.account_base.views import createbalancesheet, \
    GetFormFragmentView, AccountsView, CreateAccounts, UpdateBalanceView

urlpatterns = [
    path('create-document/', createbalancesheet, name='test'),
    path('items/get-form/', GetFormFragmentView.as_view(), name='get_form_fragment'),
    path('items/accounts-list/', AccountsView.as_view(), name='get_accounts_list'),
    path('items/accounts-list/create', CreateAccounts.as_view(), name='create_accounts'),
    path('update/<int:pk>/', UpdateBalanceView.as_view(), name='UpdateBalanceView'),
    # path('submit-forms-ajax/', SubmitFormsAjaxView.as_view(), name='submit_forms_ajax'),
]