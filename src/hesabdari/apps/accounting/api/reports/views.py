from django.db.models import Prefetch
from django.shortcuts import render
from django.views import generic

from hesabdari.apps.accounting.models.accounts import AccountsClass
from hesabdari.apps.accounting.models.balancesheet import BalanceSheet


def account_report(request):
    return render(request, 'account_base/accounts-report.html')

class AccountReportDetails(generic.View):
    def get(self, request, pk):
        parent_account = AccountsClass.objects.filter(pk=pk, user=request.user)
        descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
            Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user))))
        created_at_from = request.GET.get('created_at_from')
        created_at_to = request.GET.get('created_at_to')
        if created_at_from and created_at_to:
            descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
                Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user,
                                                                                document__date_created__gte=created_at_from,
                                                                                document__date_created__lte=created_at_to))))
        elif created_at_from:
            descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
                Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user,
                                                                                document__date_created__gte=created_at_from))))
        elif created_at_to:
            descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
                Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user,
                                                                                document__date_created__lte=created_at_to))))
        qs = []
        id_lists = []
        for descendant in descendants:
            for balance in descendant.balance_sheets.all():
                qs.append(balance)
                id_lists.append(balance.id)
        qs = sorted(qs, key=lambda b: b.document.date_created, reverse=True)
        context = {
            'balance_lists': qs,
            'id_lists': id_lists,

        }

        return render(request, 'account_base/balance_list.html', context)