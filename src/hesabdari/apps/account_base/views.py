import json
import time
from collections import namedtuple
from itertools import zip_longest
from keyword import kwlist
from lib2to3.fixes.fix_input import context

import jdatetime
import uuid

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, DatabaseError
from django.db.models import Q, Prefetch, Max, Sum, Case, IntegerField, When, F
from django.db.transaction import commit
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.template.base import kwarg_re
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.views import generic
from django.views.decorators.http import require_POST

from hesabdari.apps.account_base.forms import BalanceSheetForm, CashierChequeForm, \
    DocumentForm, AccountsForm
from hesabdari.apps.account_base.models import AccountsClass, Document, BalanceSheet, CashierCheque

User = get_user_model()

# Create your views here.
def add_month_to_jalali_date(jdate):
    # فرض: jdate = jdatetime.date(1402, 12, 10)
    year = jdate.year
    month = jdate.month + 1
    day = jdate.day

    if month > 12:
        month = 1
        year += 1

    # جلوگیری از روزهای نامعتبر (مثلاً 31 در ماه‌های 30 روزه)
    try:
        new_date = jdatetime.date(year, month, day)
    except ValueError:
        new_date = jdatetime.date(year, month, 1)  # یا آخر ماه قبلی رو بگیر

    return new_date


def extract_all_prefixes(post_data, file_data):
    prefixes = set()
    combined_keys = list(post_data.keys()) + list(file_data.keys())

    for key in combined_keys:
        if '-new' in key:
            prefix = key.split('-')[0]
            prefixes.add(prefix)
    return prefixes
TOKEN_TTL = 30 * 60  # ⏱ مدت اعتبار توکن = ۳۰ دقیقه (ثانیه)


def _get_tokens(session):
    """
    توکن‌ها رو از session بگیر و منقضی‌ها رو حذف کن
    خروجی: دیکشنری {token: timestamp}
    """
    now = time.time()
    tokens = session.get("form_tokens", {})
    # فقط توکن‌هایی رو نگه دار که هنوز منقضی نشدن
    tokens = {t: ts for t, ts in tokens.items() if now - ts < TOKEN_TTL}
    session["form_tokens"] = tokens
    return tokens


@login_required
def createbalancesheet(request):
    if request.method == "GET":
        tokens = _get_tokens(request.session)
        token = str(uuid.uuid4())
        tokens[token] = time.time()
        request.session["form_tokens"] = tokens
        document_instance = DocumentForm(initial={'user': request.user})
        context = {
            'all_balanceforms': [],
            'all_chequeforms': [],
            'document_instance': document_instance,
            'form_token': token,
        }
        return render(request, 'account_base/create-document.html', context)
    all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
    document_instance = DocumentForm(request.POST or None, initial={'user':request.user})
    all_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i in all_prefixes]
    all_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]
    if request.method == "POST":
        tokens = _get_tokens(request.session)
        token = request.POST.get("form_token")

        # چک کردن اعتبار توکن
        if token not in tokens:
            return JsonResponse({
                "success": False,
                "errors": "این فرم قبلاً ارسال شده، نامعتبر یا منقضی شده است."
            }, status=400)
        all_credit = 0
        all_debt = 0
        all_forms_valid = True
        for balance, cheque in zip(all_balanceforms, all_chequeforms):
            if not balance.is_valid() or not cheque.is_valid():
                all_forms_valid = False
                print(balance.prefix)
                return JsonResponse({
                    "success": False,
                    "errors": render_to_string("partials/errors.html", {"form": balance, 'err_id':balance.prefix}, request=request)
                })

        if not document_instance.is_valid():
            all_forms_valid = False
            return JsonResponse({'success': False, 'errors': document_instance.errors}, )

        if all_forms_valid:
            d=document_instance.save(commit=False)
            for balance in all_balanceforms:
                if balance.cleaned_data.get('transaction_type') == "debt":
                    all_debt += balance.cleaned_data.get('amount') or 0
                elif balance.cleaned_data.get('transaction_type') == "credit":
                    all_credit += balance.cleaned_data.get('amount') or 0

            if all_credit != all_debt:
                return JsonResponse({'success': False, 'errors': 'مجموع بدهکاری و بستانکاری برابر نیست.'},)
            else:
                try:
                    with transaction.atomic():
                        d.save()
                        document_instance.save()
                        for balance, cheque in zip(all_balanceforms, all_chequeforms):
                            b = balance.save(commit=False)
                            if cheque.cleaned_data.get('name'):
                                c = cheque.save()
                                b.cheque = c
                            b.document = d
                            b.save()
                except DatabaseError as e:  # یا Exception برای هر خطای غیرمنتظره
                    return JsonResponse({
                        "success": False,
                        "errors": "مشکلی در ذخیره اطلاعات پیش آمد. دوباره تلاش کنید."
                        # اگر خواستی برای دیباگ:  f"خطا: {str(e)}"
                    }, status=500)
                try:
                    tokens.pop(token, None)
                    request.session["form_tokens"] = tokens
                    return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")},)
                except KeyError:
                    return JsonResponse({'success': False, 'errors': 'testieeee'}, )

    context = {
        'all_balanceforms': all_balanceforms,
        'all_chequeforms': all_chequeforms,
        'document_instance': document_instance
    }

    return render(request, 'account_base/create-document.html', context)


class GetFormFragmentView(generic.View):
    def post(self, request):
        if request.POST.get('maturity_date'):
            datease = request.POST.get('maturity_date')
            datease = str(add_month_to_jalali_date(jdatetime.date.fromisoformat(datease)))
        else:
            datease = ''
        uniqueid = str(uuid.uuid1())[:4]
        transaction_type = request.POST.get('transaction_type')

        form_balance = BalanceSheetForm(prefix=f'{uniqueid}-new-balance', initial={'transaction_type': transaction_type, 'user':request.user.id})
        if transaction_type == 'debt':
            form_cheque = CashierChequeForm(prefix=f'{uniqueid}-new-cheque', initial={'user': request.user.id, 'cheque_type': 'دریافتنی'})
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance,'form_cheque':form_cheque,
                                          'transaction_type':transaction_type, 'uniqueid':uniqueid})
        else:
            form_cheque = CashierChequeForm(prefix=f'{uniqueid}-new-cheque', initial={'user': request.user.id, 'cheque_type': 'پرداختنی'})
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance, 'form_cheque': form_cheque,
                                          'transaction_type': transaction_type, 'uniqueid':uniqueid})
        return JsonResponse({'form_html': form_html, 'datease':datease })


def account_report(request):
    return render(request, 'account_base/accounts-report.html')
# class AccountsView(generic.View):
#     def get(self, request):
#         def serialize_node(node, net_total):
#             return {
#                 'id': str(node.id),
#                 'text': node.name,
#                 'parent': str(node.parent.id) if node.parent else '#',
#                 'li_attr': {'data-net-total': net_total},
#             }
#
#         accounts = AccountsClass.objects.filter(user=request.user).prefetch_related(
#             Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user)))
#         data= []
#         for account in accounts:
#             descendants = account.get_descendants(include_self=True)
#             total_debtor = 0
#             total_creditor = 0
#             for descendant in descendants:
#                 for bs in descendant.balance_sheets.all():
#                     if bs.amount:
#                         if bs.transaction_type == 'debt':
#                             total_debtor += bs.amount
#                         elif bs.transaction_type == 'credit':
#                             total_creditor += bs.amount
#
#             net_total = total_creditor - total_debtor
#
#             data.append(serialize_node(account, net_total))
#         form_html = render_to_string('account_base/accounts.html', {
#             'uniqueid': request.GET.get('uid', 'default')
#         })
#         return JsonResponse({'form_html': form_html, 'data': data})

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
            balances = balances.filter(user=request.user,document__date_created__lte=end_date)

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


class AccountReportDetails(generic.View):
    def get(self, request, pk):
        parent_account = AccountsClass.objects.filter(pk=pk, user=request.user)
        descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
        Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user))))
        created_at_from = request.GET.get('created_at_from')
        created_at_to = request.GET.get('created_at_to')
        if created_at_from and created_at_to:
            descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
                Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user, document__date_created__gte=created_at_from, document__date_created__lte=created_at_to))))
        elif created_at_from:
            descendants = (parent_account.get_descendants(include_self=True).prefetch_related(
                Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user, document__date_created__gte=created_at_from))))
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
            'balance_lists':qs,
            'id_lists': id_lists,

        }

        return render(request, 'account_base/balance_list.html', context)


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



def extract_all_update_prefixes(post_data, file_data):
    prefixes = set()
    combined_keys = list(post_data.keys()) + list(file_data.keys())

    for key in combined_keys:
        if '-update' in key:
            prefix = key.split('-')[0]
            prefixes.add(prefix)
    return prefixes


CombinedForm = namedtuple(
    'CombinedForm',
    ['uniqueid', 'form_balance', 'form_cheque', 'chequeid', 'account_str', 'bank_str', 'balance_id', 'is_active']
)

PostCombinedForm = namedtuple(
    'PostCombinedForm',
    ['uniqueid', 'form_balance', 'form_cheque']
)


class UpdateBalanceView(LoginRequiredMixin, generic.View):

    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        document_form = DocumentForm(request.POST or None, instance=document)

        balancesheets = (
            BalanceSheet.objects
            .filter(document=document)
            .select_related("account", "cheque__account")     # FK ها
            .prefetch_related("cheque__balance_sheet")        # reverse relation
        )

        combined_forms = []
        for balance in balancesheets:
            balance_form = BalanceSheetForm(prefix=f"{balance.id}-update-balance", instance=balance)
            if balance.transaction_type == 'debt':
                cheque_form = (
                    CashierChequeForm(prefix=f"{balance.id}-update-cheque", instance=balance.cheque)
                    if balance.cheque else
                    CashierChequeForm(prefix=f"{balance.id}-update-cheque", initial={'cheque_type': 'دریافتنی'})
                )
            else:
                cheque_form = (
                    CashierChequeForm(prefix=f"{balance.id}-update-cheque", instance=balance.cheque)
                    if balance.cheque else
                    CashierChequeForm(prefix=f"{balance.id}-update-cheque", initial={'cheque_type': 'پرداختنی'})
                )

            combined_forms.append(CombinedForm(
                uniqueid=balance.id,
                form_balance=balance_form,
                form_cheque=cheque_form,
                chequeid=getattr(balance.cheque, 'id', None),
                account_str=str(balance.account),
                bank_str=str(balance.cheque.account) if balance.cheque else "----",
                balance_id=balance.id,
                is_active=balance.is_active,
            ))

        context = {
            'combined_forms': combined_forms,
            'document_id': document.id,
            'document_instance': document_form,
        }
        return render(request, "account_base/create-document.html", context)

    @transaction.atomic
    def post(self, request, pk):
        next_url = request.GET.get('next')
        deleted_ids = json.loads(request.POST.get('deleted_balances_id', '[]'))
        document = get_object_or_404(Document, pk=pk)
        document_form = DocumentForm(request.POST or None, instance=document)

        user = request.user
        balancesheets = (
            BalanceSheet.objects
            .filter(user=user, document=document)
            .select_related("account", "cheque__account")     # FK ها
            .prefetch_related("cheque__balance_sheet")        # reverse relation
        )

        combined_forms = []
        all_credit, all_debt, all_valid = 0, 0, True
        to_delete = []
        for balance in balancesheets:
            if not balance.is_active:
                if balance.transaction_type == "debt":
                    all_debt += balance.amount or 0
                elif balance.transaction_type == "credit":
                    all_credit += balance.amount or 0
                continue

            if balance.id in deleted_ids:
                to_delete.append(balance)
                continue

            balance_form = BalanceSheetForm(
                request.POST, request.FILES, prefix=f"{balance.id}-update-balance", instance=balance
            )
            cheque_form = CashierChequeForm(
                request.POST or None, prefix=f"{balance.id}-update-cheque", instance=balance.cheque
            )

            combined_forms.append(PostCombinedForm(balance.id, balance_form, cheque_form))

            if not balance_form.is_valid() or not cheque_form.is_valid():
                all_valid = False

            all_debt, all_credit = self._update_totals(balance_form, all_debt, all_credit)

        # new balances
        all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
        new_balance_forms = [
            BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{prefix}-new-balance')
            for prefix in all_prefixes
        ]
        new_cheque_forms = [
            CashierChequeForm(request.POST or None, prefix=f'{prefix}-new-cheque')
            for prefix in all_prefixes
        ]

        for bal_form, cheque_form in zip(new_balance_forms, new_cheque_forms):
            if not bal_form.is_valid() or not cheque_form.is_valid():
                all_valid = False

        if not document_form.is_valid():
            all_valid = False

        if all_valid:
            for bal_form in new_balance_forms:
                all_debt, all_credit = self._update_totals(bal_form, all_debt, all_credit)

            if all_credit != all_debt:
                return JsonResponse({'success': False, 'errors': 'مجموع بدهکاری و بستانکاری برابر نیست.'})

            for balance in to_delete:
                self._handle_delete(balance)

            # ذخیره همه چیز در یک تراکنش اتمیک
            self._save_existing_forms(combined_forms, document, user, document_form)
            self._save_new_forms(new_balance_forms, new_cheque_forms, document, user, document_form)
            if next_url:
                return JsonResponse({'success': True, "redirect_url": next_url})
            else:
                return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")})

        context = {
            'documentform': document,
            'all_balanceforms': new_balance_forms,
            'all_chequeforms': new_cheque_forms,
            'form_action_url': reverse('UpdateBalanceView', args=[pk])
        }
        return render(request, 'account_base/create-document.html', context)

    # ---------------- Helper Methods ---------------- #

    def _handle_delete(self, balance):
        balance.delete()
        if balance.cheque:
            last_inactive = balance.cheque.balance_sheet.filter(is_active=False).last()
            if last_inactive:
                last_inactive.is_active = True
                last_inactive.save()
            else:
                balance.cheque.delete()

    def _update_totals(self, form, all_debt, all_credit):
        tx_type = form.cleaned_data.get('transaction_type')
        amount = form.cleaned_data.get('amount') or 0
        if tx_type == "debt":
            all_debt += amount
        elif tx_type == "credit":
            all_credit += amount
        return all_debt, all_credit

    def _save_existing_forms(self, combined_forms, document, user, document_form):
        for item in combined_forms:
            balance = item.form_balance.save(commit=False)
            if item.form_cheque.cleaned_data.get('name'):
                cheque = item.form_cheque.save(commit=False)
                cheque.user = user
                if cheque.cheque_type is None:
                    if balance.transaction_type == 'debt':
                        cheque.cheque_type = 'دریافتنی'
                    else:
                        cheque.cheque_type = 'پرداختنی'
                cheque.save()
                balance.cheque = cheque
            balance.document = document
            balance.save()
            document_form.save()

    def _save_new_forms(self, balance_forms, cheque_forms, document, user, document_form):
        for bal_form, cheque_form in zip(balance_forms, cheque_forms):
            balance = bal_form.save(commit=False)
            balance.user = user
            if cheque_form.cleaned_data.get('name'):
                cheque = cheque_form.save(commit=False)
                cheque.user = user
                cheque.save()
                balance.cheque = cheque
            balance.document = document
            balance.save()
            document_form.save()

@login_required
@require_POST
def deletechequeview(request):
    cheque_id = request.POST.get('cheque_id')
    if not cheque_id:
        return JsonResponse({'success': False, 'error': 'شناسه چک ارسال نشده'})

    cheque = CashierCheque.objects.filter(pk=cheque_id, user=request.user).first()
    if cheque is None:
        return JsonResponse({'success': False, 'error': 'چک پیدا نشد'})
    elif BalanceSheet.objects.filter(cheque=cheque, is_active=False).exists():
        return JsonResponse({'success': False, 'error': 'این چک در سند دیگر هم در حال استفاده است.'})
    else:
        cheque.delete()
    return JsonResponse({'success': True})



class ChequeListView(LoginRequiredMixin, generic.View):
    def get(self, request):
        qs = BalanceSheet.objects.filter(
            user=request.user.id,
            cheque__isnull=False,
            is_active=True
        ).select_related('cheque')

        aggregates = qs.aggregate(
            receivables_debt=Sum(
                Case(
                    When(cheque__cheque_type='دریافتنی', transaction_type='debt', then='amount'),
                    output_field=IntegerField(),
                )
            ),
            receivables_credit=Sum(
                Case(
                    When(cheque__cheque_type='دریافتنی', transaction_type='credit', then='amount'),
                    output_field=IntegerField(),
                )
            ),
            payables_debt=Sum(
                Case(
                    When(cheque__cheque_type='پرداختنی', transaction_type='debt', then='amount'),
                    output_field=IntegerField(),
                )
            ),
            payables_credit=Sum(
                Case(
                    When(cheque__cheque_type='پرداختنی', transaction_type='credit', then='amount'),
                    output_field=IntegerField(),
                )
            ),
        )
        payables_debt_amount = aggregates['payables_debt'] or 0
        payables_credit_amount = aggregates['payables_credit'] or 0
        receivables_debt_amount = aggregates['receivables_debt'] or 0
        receivables_credit_amount = aggregates['receivables_credit'] or 0

        context = {
            'receivables': qs.filter(cheque__cheque_type='دریافتنی'),
            'payables': qs.filter(cheque__cheque_type='پرداختنی'),
            'receivables_debt_amount': aggregates['receivables_debt'] or 0,
            'receivables_credit_amount': aggregates['receivables_credit'] or 0,
            'receivables_balance': receivables_debt_amount - receivables_credit_amount,
            'payables_debt_amount': aggregates['payables_debt'] or 0,
            'payables_credit_amount': aggregates['payables_credit'] or 0,
            'payables_balance': payables_debt_amount - payables_credit_amount
        }
        return render(request, 'account_base/cheque-lists.html', context)
def filter_receivable_cheques(request):
    receivables = BalanceSheet.objects.filter(
        user=request.user.id,
        cheque__cheque_type='دریافتنی',
        cheque__isnull=False,
        is_active=True
    ).select_related('cheque').only(
        'cheque__name',
        'cheque__cheque_status',
        'cheque__maturity_date',
        'amount',
        'description',
        'cheque__cheque_type'
    )

    # فیلترها
    name = request.GET.get('cheque_name')
    status = request.GET.get('cheque_status')
    amount = request.GET.get('amount')
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if due_date_from:
        receivables = receivables.filter(cheque__maturity_date__gte=due_date_from)
    if due_date_to:
        receivables = receivables.filter(cheque__maturity_date__lte=due_date_to)
    if created_at_from:
        receivables = receivables.filter(document__date_created__gte=created_at_from)
    if created_at_to:
        receivables = receivables.filter(document__date_created__lte=created_at_to)
    if amount:
        receivables = receivables.filter(amount=amount)
    if status:
        receivables = receivables.filter(cheque__cheque_status=status)
    if name:
        receivables = receivables.filter(cheque__name__icontains=name)
    if description:
        receivables = receivables.filter(description__contains=description)

    # محاسبه جمع‌ها
    aggregates = receivables.aggregate(
        debt=Sum(
            Case(
                When(transaction_type='debt', then='amount'),
                output_field=IntegerField(),
            )
        ),
        credit=Sum(
            Case(
                When(transaction_type='credit', then='amount'),
                output_field=IntegerField(),
            )
        ),
    )

    receivables_debt_amount = aggregates['debt'] or 0
    receivables_credit_amount = aggregates['credit'] or 0

    # رندر لیست به html
    html = render_to_string('partials/receivable_cheques.html', {'receivables': receivables})

    return JsonResponse({
        'html': html,
        'receivables_debt_amount': receivables_debt_amount,
        'receivables_credit_amount': receivables_credit_amount,
    })

def filter_credit_cheques(request):
    payables = BalanceSheet.objects.filter(
        user=request.user.id,
        cheque__cheque_type='پرداختنی',
        cheque__isnull=False,
        is_active=True
    ).select_related('cheque').only(
        'cheque__name',
        'cheque__cheque_status',
        'cheque__maturity_date',
        'cheque__created_at',
        'amount',
        'description',
        'cheque__cheque_type'
    )

    # فیلترها
    name = request.GET.get('cheque_name')
    status = request.GET.get('cheque_status')
    amount = request.GET.get('amount')
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if due_date_from:
        payables = payables.filter(cheque__maturity_date__gte=due_date_from)
    if due_date_to:
        payables = payables.filter(cheque__maturity_date__lte=due_date_to)
    if created_at_from:
        payables = payables.filter(document__date_created__gte=created_at_from)
    if created_at_to:
        payables = payables.filter(document__date_created__lte=created_at_to)
    if amount:
        payables = payables.filter(amount=amount)
    if status:
        payables = payables.filter(cheque__cheque_status=status)
    if name:
        payables = payables.filter(cheque__name__icontains=name)
    if description:
        payables = payables.filter(description__contains=description)

    # محاسبه جمع‌ها
    aggregates = payables.aggregate(
        debt=Sum(
            Case(
                When(transaction_type='debt', then='amount'),
                output_field=IntegerField(),
            )
        ),
        credit=Sum(
            Case(
                When(transaction_type='credit', then='amount'),
                output_field=IntegerField(),
            )
        ),
    )

    payables_debt_amount = aggregates['debt'] or 0
    payables_credit_amount = aggregates['credit'] or 0

    # رندر لیست به html
    html = render_to_string('partials/payable_cheques.html', {'payables': payables})

    return JsonResponse({
        'html': html,
        'payables_debt_amount': payables_debt_amount,
        'payables_credit_amount': payables_credit_amount,
    })


def edit_account(request, pk):
    account = get_object_or_404(AccountsClass, pk=pk, user=request.user)
    name = request.POST.get('name')
    if name:
        account.name = name
        account.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'نام خالی است'})


@login_required
@require_POST
def delete_document(request, pk):
    # document = get_object_or_404(
    #     Document.objects.prefetch_related('items__cheque__balance_sheet'),
    #     pk=pk,
    #     user=request.user
    # )
    document = Document.objects.prefetch_related('items__cheque__balance_sheet').filter(pk=pk,
        user=request.user)
    # checks if any balance is false
    if document.items.filter(is_active=False).exists():
        return JsonResponse({
            "success": False,
            "error": "به دلیل وجود تراکنش غیر فعال، امکان حذف این سند وجود ندارد."
            # اگر خواستی برای دیباگ:  f"خطا: {str(e)}"
        })

    # find all cheques in document
    cheque_ids = document.items.filter(cheque__isnull=False).values_list('cheque_id', flat=True)

    if cheque_ids:
        # 3) آپدیت مستقیم balance_sheet های غیرفعال آخرین چک‌ها
        #    اینجا فرض می‌کنیم هر cheque فقط یک balance_sheet غیرفعال نیاز به فعال‌سازی داره

        last_inactive = (
            BalanceSheet.objects
            .filter(cheque_id__in=cheque_ids, is_active=False)
            .values('cheque_id')
            .annotate(last_id=Max('id'))  # آخرین رکورد برای هر cheque
        )
        # get latest ids
        last_ids = [item['last_id'] for item in last_inactive]
        if last_ids:
            BalanceSheet.objects.filter(id__in=last_ids).update(is_active=True)
    # delete document
    document.delete()
    return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")}, )



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

class BalanceListView(LoginRequiredMixin, generic.View):
    def get(self, request):
        qs = BalanceSheet.objects.select_related('cheque', 'document').filter(user=request.user.id).order_by('-document__date_created')
        aggregates = qs.aggregate(
            debt=Sum(
                Case(
                    When(transaction_type='debt', then='amount'),
                    output_field=IntegerField(),
                )
            ),
            credit=Sum(
                Case(
                    When(transaction_type='credit', then='amount'),
                    output_field=IntegerField(),
                )
            ),

        )



        total_debt = aggregates['debt'] or 0
        total_credit = aggregates['credit'] or 0
        running_total = 0
        running_debt_total = 0
        running_credit_total = 0
        for obj in qs:
            if obj.transaction_type == 'debt':
                running_debt_total += obj.amount
            else:
                running_credit_total += obj.amount
            running_total = running_debt_total - running_credit_total
            obj.jame_amount = running_total
            # print(running_total)
        total_balance = total_debt - total_credit
        context = {
            'balance_lists': qs,
            'total_debt': total_debt,
            'total_credit': total_credit,
            'total_balance': total_balance,
        }
        return render(request, 'account_base/balance_list.html', context)


def filter_balance(request):
    current_day = jdatetime.date.today()
    if request.GET.get('id_lists'):
        id_lists_json = request.GET.get('id_lists', '[]')
        id_lists = json.loads(id_lists_json)
        id_lists = [int(i) for i in id_lists]
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id, id__in=id_lists),
        ).order_by('-document__date_created').select_related('document')
    else:
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id)).order_by('-document__date_created')

    account_id = request.GET.get('account_id')
    amount = request.GET.get('amount')
    balance_id = request.GET.get('balance_id')
    document_id = request.GET.get('document_id')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')
    debt_condition = {'transaction_type':'debt'}
    credit_condition = {'transaction_type':'credit'}
    if balance_id:
        qs = qs.filter(id = int(balance_id))
    if document_id:
        qs = qs.filter(document_id = document_id)
    if amount:
        qs = qs.filter(amount=amount)
    if description:
        qs = qs.filter(description__contains=description)
    if account_id:
        accounts = AccountsClass.objects.get(id=account_id)
        accounts = accounts.get_descendants(include_self=True)
        qs = qs.filter(account__in=accounts)
        #qs = qs.filter(account__name__contains=account_name)
    pre_qs = qs

    if created_at_from:
        debt_condition['document__date_created__lt'] = created_at_from
        credit_condition['document__date_created__lt'] = created_at_from
        if created_at_from == created_at_to:
            qs = qs.filter(document__date_created__exact=created_at_from)
        else:
            qs = qs.filter(document__date_created__gte=created_at_from)
    if created_at_to:
        if created_at_from == created_at_to:
            qs = qs.filter(document__date_created__exact=created_at_to)
        else:
            qs = qs.filter(document__date_created__lte=created_at_to)

    aggregates = qs.aggregate(
        debt=Sum(
            Case(
                When(transaction_type='debt',
                     then='amount'),
                output_field=IntegerField(),
            )
        ),
        credit=Sum(
            Case(
                When(transaction_type='credit',
                     then='amount'),
                output_field=IntegerField(),
            )
        ),
    )

    default_date = jdatetime.date(current_day.year, 1, 1)
    for cond in (debt_condition, credit_condition):
        cond.setdefault('document__date_created__lt', default_date)

    pre_aggregates = pre_qs.aggregate(
        pre_debt=Sum(
            Case(
                When(**debt_condition, then='amount'),
                output_field=IntegerField(),
            )
        ),
        pre_credit=Sum(
            Case(
                When(**credit_condition, then='amount'),
                output_field=IntegerField(),
            )
        ),
    )


    pre_total_credit = pre_aggregates['pre_credit'] or 0
    pre_total_debt = pre_aggregates['pre_debt'] or 0
    sum_debt = aggregates['debt'] or 0
    sum_credit = aggregates['credit'] or 0
    total_debt = pre_total_debt + sum_debt
    total_credit = pre_total_credit + sum_credit
    html = render_to_string('partials/search_balance.html', {'balance_lists': qs})
    return JsonResponse({'html': html, 'total_debt': total_debt, 'total_credit':total_credit, 'pre_total_credit':pre_total_credit, 'pre_total_debt':pre_total_debt})

class ChangeStatusCheque(generic.View):
    def get(self, request, pk):
        balancesheet = get_object_or_404(BalanceSheet, id=pk, user=request.user, is_active=True)
        document = DocumentForm(request.POST or None, initial={'user':request.user})
        combined_forms = []
        locked = True
        combined_form = namedtuple('combined_form',
                                   ['uniqueid', 'form_balance', 'form_cheque', 'chequeid', 'bank_str',
                                    'balance_id', 'account_str', 'locked'])
        if balancesheet.transaction_type == 'debt':
            balance_forms = BalanceSheetForm(prefix=f"old-update-cheque-update-balance", initial={"user":request.user, "transaction_type":'credit', 'amount':balancesheet.amount, 'account':balancesheet.account})
        else:
            balance_forms = BalanceSheetForm(prefix=f"old-update-cheque-update-balance", initial={"user":request.user, "transaction_type": 'debt', 'amount':balancesheet.amount, 'account':balancesheet.account})
        balance_id = 'old-update-balance'
        cheque_forms = CashierChequeForm(prefix=f"old-update-cheque-update-cheque", instance=balancesheet.cheque)
        chequeid = balancesheet.cheque.id
        bank_str = balancesheet.cheque.account.__str__()
        combined_forms.append(
                combined_form("old-update-cheque", balance_forms, cheque_forms, chequeid, bank_str, balance_id, balancesheet.account, locked))
        context = {
            'document_instance': document,
            'combined_forms': combined_forms,
        }
        return render(request, "account_base/create-document.html", context)
    def post(self, request, pk):
        document = DocumentForm(request.POST or None)
        balancesheet = BalanceSheet.objects.filter(id=pk, user=request.user, is_active=True).last()
        next_url = request.GET.get('next', reverse('cheque-lists-view'))
        print(balancesheet)
        all_credit = 0
        all_debt = 0
        all_valid = True
        user = request.user
        balanceCheqe = BalanceSheetForm(request.POST, request.FILES, prefix=f"old-update-cheque-update-balance")
        update_Cheqe = CashierChequeForm(request.POST or None, prefix=f"old-update-cheque-update-cheque", instance=balancesheet.cheque)
        if not balanceCheqe.is_valid() or not update_Cheqe.is_valid() or not document.is_valid():
            all_valid = False
            print('1')
            print(balanceCheqe.errors, update_Cheqe.errors)
        if balanceCheqe.cleaned_data.get('transaction_type') == "debt":
            all_debt += balanceCheqe.cleaned_data.get('amount') or 0
        elif balanceCheqe.cleaned_data.get('transaction_type') == "credit":
            all_credit += balanceCheqe.cleaned_data.get('amount') or 0
        all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
        all_new_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i
                                in
                                all_prefixes]
        all_new_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]

        for balance, cheque in zip(all_new_balanceforms, all_new_chequeforms):
            if not balance.is_valid() or not cheque.is_valid():
                all_valid = False
        if all_valid:
            for balance in all_new_balanceforms:
                if balance.cleaned_data.get('transaction_type') == "debt":
                    all_debt += balance.cleaned_data.get('amount') or 0
                elif balance.cleaned_data.get('transaction_type') == "credit":
                    all_credit += balance.cleaned_data.get('amount') or 0

            if all_credit != all_debt:
                return JsonResponse({'success': False, 'errors': 'مجموع بدهکاری و بستانکاری برابر نیست.'}, )
            else:
                # save existing balance and cheque forms
                with transaction.atomic():
                    print('atomic')
                    balancesheet.is_active = False
                    balancesheet.save()
                    d = document.save()
                    new_change_balance = balanceCheqe.save(commit=False)
                    change_cheque = update_Cheqe.save()
                    new_change_balance.document = d
                    new_change_balance.cheque = change_cheque
                    new_change_balance.save()

                    # save new balance and cheque forms
                    for balance, cheque in zip(all_new_balanceforms, all_new_chequeforms):
                        b = balance.save(commit=False)
                        b.user = user
                        if cheque.cleaned_data.get('name'):
                            c = cheque.save(commit=False)
                            c.user = user
                            c.save()
                            b.cheque = c
                        b.document = d
                        b.save()
                if next_url:
                    return JsonResponse({'success': True, "redirect_url": next_url}, )
                else:
                    return JsonResponse({'success': True, "redirect_url": reverse("cheque-lists-view")}, )

        context = {
            'documentform': document,
            'all_balanceforms': all_new_balanceforms,
            'all_chequeforms': all_new_chequeforms,
            'form_action_url': reverse('change_status_cheque', args=[pk])
        }

        return render(request, 'account_base/create-document.html', context)




