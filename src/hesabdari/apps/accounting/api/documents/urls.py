from django.urls import path

from hesabdari.apps.accounting.api.documents.views import createbalancesheet, GetFormFragmentView, UpdateBalanceView, \
    delete_document

urlpatterns = [
    path('create-document/', createbalancesheet, name='create-document'),
    path('items/get-form/', GetFormFragmentView.as_view(), name='get_form_fragment'),
    path('update/<int:pk>/', UpdateBalanceView.as_view(), name='UpdateBalanceView'),
    path('delete-document/<int:pk>/', delete_document, name='delete_document'),
    ]

