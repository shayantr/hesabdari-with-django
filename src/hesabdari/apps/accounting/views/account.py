import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views import generic

from hesabdari.apps.accounting.forms import AccountsForm
from hesabdari.apps.accounting.models import AccountsClass, BalanceSheet


def accouns_manager(request):
    return render(request, 'account_base/accounts-manager.html', {})

class AccountsView(generic.View):
    def get(self, request):
        def serialize_node(node, net_total):
            return {
                'id': str(node.id),
                'text': node.name,
                'parent': str(node.parent.id) if node.parent else '#',
                'li_attr': {'data-net-total': net_total},
            }

        # همه‌ی حساب‌ها رو با parent واکشی کن
        accounts = AccountsClass.objects.filter(user=request.user).select_related('parent')
        balances = BalanceSheet.objects.filter(user=request.user)
        # همه‌ی تراکنش‌های کاربر رو یکجا بگیر
        if request.GET.get('start-date'):
            start_date = str(request.GET.get('start-date'))
            balances = balances.filter(user=request.user, document__date_created__gte=start_date)
        if request.GET.get('end-date'):
            end_date = str(request.GET.get('end-date'))
            balances = balances.filter(user=request.user, document__date_created__lte=end_date)

        # جمع تراکنش‌ها بر اساس account_id
        totals = balances.values('account_id', 'transaction_type').annotate(total=Sum('amount'))

        # دیکشنری برای دسترسی سریع
        totals_dict = {}
        for row in totals:
            acc_id = row['account_id']
            ttype = row['transaction_type']
            amount = row['total'] or 0
            if acc_id not in totals_dict:
                totals_dict[acc_id] = {'debt': 0, 'credit': 0}
            totals_dict[acc_id][ttype] += amount

        data = []
        for account in accounts:
            # گرفتن descendantها (از treebeard یا mptt فرض می‌کنیم)
            descendants = account.get_descendants(include_self=True)

            total_debtor = 0
            total_creditor = 0
            for desc in descendants:
                if desc.id in totals_dict:
                    total_debtor += totals_dict[desc.id]['debt']
                    total_creditor += totals_dict[desc.id]['credit']

            net_total = total_creditor - total_debtor
            data.append(serialize_node(account, net_total))

        form_html = render_to_string('account_base/accounts.html', {
            'uniqueid': request.GET.get('uid', 'default')
        })

        return JsonResponse({'form_html': form_html, 'data': data})

def create_accounts(request):
    parent_id = request.POST.get('parent')
    form = AccountsForm(request.POST)
    if form.is_valid():
        new_account = form.save(commit=False)
        new_account.user = request.user
        if parent_id:
            new_account.parent_id = parent_id
        else:
            new_account.parent = None
        new_account.save()
        return JsonResponse({
            'success': True,
            'id': new_account.id,
            'name': new_account.name,
            'parent_id': new_account.parent.id if new_account.parent else None
        })
    else:
        return JsonResponse({'success': False, 'errors': form.errors})

def edit_account(request, pk):
    account = get_object_or_404(AccountsClass, pk=pk, user=request.user)
    name = request.POST.get('name')
    if name:
        account.name = name
        account.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'نام خالی است'})

def delete_account(request, pk):
    if request.method == 'POST':
        try:
            account = AccountsClass.objects.get(pk=pk, user=request.user)
            if account.get_children():
                return JsonResponse({'success': False, 'error': 'این حساب زیرمجموعه دارد'})
            if BalanceSheet.objects.filter(user=request.user.id).filter(account=account).exists():
                return JsonResponse({'success': False, 'error': 'این حساب در سندی در حال استفاده است.'})
            else:
                account.delete()
                return JsonResponse({'success': True})
        except AccountsClass.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'حساب پیدا نشد'})
    else:
        raise Http404()

class UpdateBulkAccount(LoginRequiredMixin, generic.View):
    def post(self, request):
        data = json.loads(request.body)
        selected_ids = data.get("balances", [])
        transfer_value = data.get("transfer_value")
        balances = BalanceSheet.objects.filter(user=request.user,id__in=selected_ids)
        for balance in balances:
            balance.account_id = int(transfer_value)
        BalanceSheet.objects.bulk_update(balances, ['account_id'])
        return JsonResponse({"status": "ok", "received": selected_ids})