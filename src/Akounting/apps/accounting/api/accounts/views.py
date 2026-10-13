import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.views import generic
from mptt.exceptions import InvalidMove

from Akounting.apps.accounting.forms import AccountsForm
from Akounting.apps.accounting.models.accounts import AccountsClass
from Akounting.apps.accounting.models.balancesheet import BalanceSheet


@login_required
def accouns_manager(request):
    return render(request, 'account_base/accounts-manager.html', {})


class AccountsView(LoginRequiredMixin, generic.View):
    def get(self, request):
        def serialize_node(node, net_total, path):
            return {
                'id': str(node.id),
                'text': node.name,
                'parent': str(node.parent.id) if node.parent else '#',
                'li_attr': {'data-net-total': net_total},
                'data': {'path': path},
            }

        # همه‌ی حساب‌ها رو با parent واکشی کن
        accounts = list(AccountsClass.objects.filter(user=request.user).select_related('parent'))
        account_by_id = {account.id: account for account in accounts}
        path_cache = {}

        def account_path(account):
            if account.id in path_cache:
                return path_cache[account.id]

            names = [account.name]
            parent_id = account.parent_id
            visited = {account.id}
            while parent_id and parent_id not in visited:
                visited.add(parent_id)
                parent = account_by_id.get(parent_id)
                if parent is None:
                    break
                names.append(parent.name)
                parent_id = parent.parent_id

            path_cache[account.id] = ' > '.join(reversed(names))
            return path_cache[account.id]

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
            data.append(serialize_node(account, net_total, account_path(account)))

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


@login_required
@require_POST
def move_account(request, pk):
    """Move an account subtree to an exact zero-based sibling position."""
    try:
        payload = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'اطلاعات جابه‌جایی معتبر نیست.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'success': False, 'error': 'اطلاعات جابه‌جایی معتبر نیست.'}, status=400)

    if 'parent_id' not in payload:
        return JsonResponse({'success': False, 'error': 'حساب مقصد مشخص نشده است.'}, status=400)

    parent_id = payload.get('parent_id')
    position = payload.get('position')

    if isinstance(position, bool) or not isinstance(position, int):
        return JsonResponse({'success': False, 'error': 'موقعیت حساب معتبر نیست.'}, status=400)

    if parent_id is not None and (isinstance(parent_id, bool) or not isinstance(parent_id, int)):
        return JsonResponse({'success': False, 'error': 'حساب مقصد معتبر نیست.'}, status=400)

    with transaction.atomic():
        # Root moves can renumber tree IDs belonging to other users too, so the
        # complete MPTT table is locked while a new position is calculated.
        locked_accounts = AccountsClass.objects.select_for_update().all()
        list(locked_accounts.values_list('pk', flat=True))

        account = AccountsClass.objects.filter(pk=pk, user=request.user).first()
        if account is None:
            return JsonResponse({'success': False, 'error': 'حساب پیدا نشد.'}, status=404)
        new_parent = None
        if parent_id is not None:
            new_parent = AccountsClass.objects.filter(pk=parent_id, user=request.user).first()
            if new_parent is None:
                return JsonResponse({'success': False, 'error': 'حساب مقصد پیدا نشد.'}, status=404)
            if new_parent.pk == account.pk or new_parent.is_descendant_of(account):
                return JsonResponse(
                    {'success': False, 'error': 'یک حساب را نمی‌توان داخل خودش یا زیرمجموعه‌هایش قرار داد.'},
                    status=400,
                )

        siblings = list(
            AccountsClass.objects.filter(user=request.user, parent=new_parent)
            .exclude(pk=account.pk)
            .order_by('tree_id', 'lft')
        )
        if position < 0 or position > len(siblings):
            return JsonResponse({'success': False, 'error': 'موقعیت انتخاب‌شده خارج از محدوده است.'}, status=400)

        current_sibling_ids = list(
            AccountsClass.objects.filter(user=request.user, parent_id=account.parent_id)
            .order_by('tree_id', 'lft')
            .values_list('pk', flat=True)
        )
        current_position = current_sibling_ids.index(account.pk)
        if account.parent_id == parent_id and current_position == position:
            return JsonResponse({
                'success': True,
                'id': account.pk,
                'parent_id': account.parent_id,
                'position': current_position,
            })

        try:
            if not siblings:
                account.move_to(new_parent, 'last-child') if new_parent else account.move_to(None)
            elif position == len(siblings):
                account.move_to(siblings[-1], 'right')
            else:
                account.move_to(siblings[position], 'left')
        except (InvalidMove, ValueError):
            return JsonResponse({'success': False, 'error': 'این جابه‌جایی در ساختار حساب‌ها مجاز نیست.'}, status=400)

        account.refresh_from_db(fields=['parent', 'tree_id', 'lft', 'rght', 'level'])

    return JsonResponse({
        'success': True,
        'id': account.pk,
        'parent_id': account.parent_id,
        'position': position,
    })

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
