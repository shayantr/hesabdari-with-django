from collections import namedtuple
from itertools import zip_longest
from lib2to3.fixes.fix_input import context

import jdatetime
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
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

@login_required
def createbalancesheet(request):
    all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
    # document = DocumentForm(request.POST or None)
    document_instance = Document(user=request.user)
    all_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i in all_prefixes]
    all_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]
    if request.method == "POST":
        all_credit = 0
        all_debt = 0
        all_forms_valid = True



        for balance, cheque in zip(all_balanceforms, all_chequeforms):
            if not balance.is_valid() or not cheque.is_valid():
                all_forms_valid = False

        if all_forms_valid:
            for balance in all_balanceforms:
                if balance.cleaned_data.get('transaction_type') == "debt":
                    all_debt += balance.cleaned_data.get('amount') or 0
                elif balance.cleaned_data.get('transaction_type') == "credit":
                    all_credit += balance.cleaned_data.get('amount') or 0

            if all_credit != all_debt:
                return JsonResponse({'success': False, 'errors': 'مجموع بدهکاری و بستانکاری برابر نیست.'},)
            else:
                document_instance.save()
                for balance, cheque in zip(all_balanceforms, all_chequeforms):
                    b = balance.save(commit=False)
                    if cheque.cleaned_data.get('name'):
                        c = cheque.save()
                        b.cheque = c
                    b.document = document_instance
                    b.save()
                return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")},)

    context = {
        'all_balanceforms': all_balanceforms,
        'all_chequeforms': all_chequeforms,
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
        form_cheque = CashierChequeForm(prefix=f'{uniqueid}-new-cheque', initial={'user':request.user.id})
        form_balance = BalanceSheetForm(prefix=f'{uniqueid}-new-balance', initial={'transaction_type': transaction_type, 'user':request.user.id})
        if transaction_type == 'debt':
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance,'form_cheque':form_cheque,
                                          'transaction_type':transaction_type, 'uniqueid':uniqueid})
        else:
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance, 'form_cheque': form_cheque,
                                          'transaction_type': transaction_type, 'uniqueid':uniqueid})
        return JsonResponse({'form_html': form_html, 'datease':datease })



# class AccountsView(generic.View):
#     def get(self, request):
#         list_accounts = AccountsClass.objects.all().order_by('tree_id', 'lft')
#         accountform = AccountsForm()
#         tree_data = [build_tree(root) for root in AccountsClass.get_root_nodes()]
#
#
#         form_html = render_to_string('account_base/accounts.html',
#                                      {'list_accounts': list_accounts, "accountform":accountform})
#         return JsonResponse({'form_html': form_html, 'tree_data':tree_data})
#
#     def post(self, request):
#         list_accounts = AccountsClass.objects.all()
#         print(list_accounts)
#         context = {
#             'list_accounts': list_accounts
#         }
#         return JsonResponse({'list_accounts': list_accounts })

def build_tree(node):
    return {
        'id': node.id,
        'name': node.name,
        'children': [build_tree(child) for child in node.get_children()]
    }

class AccountsView(generic.View):
    def get(self, request):
        # ترتیب نمایش درخت با استفاده از lft (برای MPTT)
        list_accounts = AccountsClass.objects.all().order_by('tree_id', 'lft')

        # فرم جدید
        accountform = AccountsForm()

        # ساختار درختی برای ارسال به JS یا نمایش پویا
        tree_data = [build_tree(root) for root in AccountsClass.objects.root_nodes()]

        # رندر HTML فرم و لیست درخت
        form_html = render_to_string(
            'account_base/accounts.html',
            {
                'list_accounts': list_accounts,
                'accountform': accountform
            },
            request=request
        )

        return JsonResponse({
            'form_html': form_html,
            'tree_data': tree_data
        })


def create_accounts(request):
    form = AccountsForm(request.POST)
    print(request.POST)
    if form.is_valid():
        new_account = form.save()
        return JsonResponse({
            'success': True,
            'id': new_account.id,
            'name': new_account.name,
            'parent_id': new_account.parent.id if new_account.parent else None
        })
    else:
        return JsonResponse({'success': False, 'errors': form.errors})

    # return JsonResponse({'success': False, 'errors': accountform.errors})


def extract_all_update_prefixes(post_data, file_data):
    prefixes = set()
    combined_keys = list(post_data.keys()) + list(file_data.keys())

    for key in combined_keys:
        if '-update' in key:
            prefix = key.split('-')[0]
            prefixes.add(prefix)
    return prefixes


class UpdateBalanceView(LoginRequiredMixin, generic.View):
    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        balancesheet = BalanceSheet.objects.filter(document=document)
        combined_forms = []
        combined_form = namedtuple('combined_form', ['uniqueid', 'form_balance', 'form_cheque', 'chequeid'])
        for i in balancesheet:
            balance_forms = BalanceSheetForm(prefix=f"{i.id}-update-balance", instance=i)
            chequeid= None
            if i.cheque:
                cheque_forms = CashierChequeForm(prefix=f"{i.id}-update-cheque", instance=i.cheque)
                chequeid = i.cheque.id
            else:
                cheque_forms = CashierChequeForm(prefix=f"{i.id}-update-cheque")
            combined_forms.append(combined_form(i.id, balance_forms, cheque_forms, chequeid))
        context = {
            'combined_forms': combined_forms
        }
        return render(request, "account_base/create-document.html", context)
    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        all_credit = 0
        all_debt = 0
        user = request.user
        balancesheets = BalanceSheet.objects.filter(document=document)
        combinedform = namedtuple('combined_form', ['uniqueid', 'form_balance', 'form_cheque'])
        combined_forms = []
        all_valid = True
        for i in balancesheets:
            balanceform = BalanceSheetForm(request.POST, request.FILES, prefix=f"{i.id}-update-balance", instance=i)
            chequeform = CashierChequeForm(request.POST or None, prefix=f"{i.id}-update-cheque", instance=i.cheque)

            combined_forms.append(combinedform(i.id, balanceform, chequeform))
            if not balanceform.is_valid() or not chequeform.is_valid():
                all_valid = False
                print("false")
            if balanceform.cleaned_data.get('transaction_type') == "debt":
                all_debt += balanceform.cleaned_data.get('amount') or 0
            elif balanceform.cleaned_data.get('transaction_type') == "credit":
                all_credit += balanceform.cleaned_data.get('amount') or 0

        all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
        all_new_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i in
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
                #save existing balance and cheque forms
                for item in combined_forms:
                    b = item.form_balance.save(commit=False)
                    if item.form_cheque.cleaned_data.get('name'):
                        c = item.form_cheque.save(commit=False)
                        c.user = user
                        c.save()
                        b.cheque = c
                    b.document = document
                    b.save()
                #save new balance and cheque forms
                for balance, cheque in zip(all_new_balanceforms, all_new_chequeforms):
                    b = balance.save(commit=False)
                    b.user = user
                    if cheque.cleaned_data.get('name'):
                        c = cheque.save(commit=False)
                        c.user = user
                        c.save()
                        b.cheque = c
                    b.document = document
                    b.save()
                return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")}, )

        context = {
            'documentform': document,
            'all_balanceforms': all_new_balanceforms,
            'all_chequeforms': all_new_chequeforms,
            'form_action_url': reverse('UpdateBalanceView', args=[pk])
        }

        return render(request, 'account_base/create-document.html', context)


@login_required
@require_POST
def deletechequeview(request):
    cheque_id = request.POST.get('cheque_id')
    if not cheque_id:
        return JsonResponse({'success': False, 'error': 'شناسه چک ارسال نشده'})

    cheque = CashierCheque.objects.filter(pk=cheque_id, user=request.user).first()
    if cheque is None:
        return JsonResponse({'success': False, 'error': 'چک پیدا نشد'})

    cheque.delete()
    return JsonResponse({'success': True})



class ChequeListView(LoginRequiredMixin, generic.View):
    def get(self, request):
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id) & Q(cheque__isnull=False)
        ).select_related('cheque')
        debits = qs.filter(transaction_type='debt')
        credits = qs.filter(transaction_type='credit')

        context = {
            'debits': debits,
            'credits': credits,
        }
        return render(request, 'account_base/cheque-lists.html', context)

def filter_debit_cheques(request):
    debits = BalanceSheet.objects.filter(
        Q(user=request.user.id),
        Q(transaction_type='debt'),
        Q(cheque__isnull=False)
    ).select_related('cheque').only(
    'cheque__name', 'cheque__cheque_status', 'cheque__maturity_date',
    'cheque__created_at', 'amount', 'description'
)

    name = request.GET.get('cheque_name')
    status = request.GET.get('cheque_status')
    amount = request.GET.get('amount')
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if due_date_from:
        debits = debits.filter(cheque__user_id=request.user.id, cheque__maturity_date__gte=due_date_from)
    if due_date_to:
        debits = debits.filter(cheque__user_id=request.user.id, cheque__maturity_date__lte=due_date_to)
    if created_at_from:
        debits = debits.filter(cheque__user_id=request.user.id, cheque__created_at__gte=created_at_from)
    if created_at_to:
        debits = debits.filter(cheque__user_id=request.user.id, cheque__created_at__lte=created_at_to)
    if amount:
        debits = debits.filter(amount=amount)
    if status:
        debits = debits.filter(cheque__user_id=request.user.id, cheque__cheque_status=status)
    if name:
        debits = debits.filter(cheque__user_id=request.user.id, cheque__name__icontains=name)
    if description:
        debits = debits.filter(description__contains=description)
    html = render_to_string('partials/debit_cheques.html', {'debits': debits})
    return JsonResponse({'html': html})

def filter_credit_cheques(request):
    credits = BalanceSheet.objects.filter(
        Q(user=request.user.id),
        Q(transaction_type='credit'),
        Q(cheque__isnull=False)
    ).select_related('cheque').only(
    'cheque__name', 'cheque__cheque_status', 'cheque__maturity_date',
    'cheque__created_at', 'amount', 'description'
)

    name = request.GET.get('cheque_name')
    status = request.GET.get('cheque_status')
    amount = request.GET.get('amount')
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if due_date_from:
        credits = credits.filter(cheque__user_id=request.user.id, cheque__maturity_date__gte=due_date_from)
    if due_date_to:
        credits = credits.filter(cheque__user_id=request.user.id, cheque__maturity_date__lte=due_date_to)
    if created_at_from:
        credits = credits.filter(cheque__user_id=request.user.id, cheque__created_at__gte=created_at_from)
    if created_at_to:
        credits = credits.filter(cheque__user_id=request.user.id, cheque__created_at__lte=created_at_to)
    if amount:
        credits = credits.filter(amount=amount)
    if status:
        credits = credits.filter(cheque__user_id=request.user.id, cheque__cheque_status=status)
    if description:
        credits = credits.filter(cheque__user_id=request.user.id, description__contains=description)
    if name:
        credits = credits.filter(cheque__user_id=request.user.id, cheque__name__icontains=name)
    print(credits)

    html = render_to_string('partials/credit_cheques.html', {'credits': credits})
    return JsonResponse({'html': html})

class BalanceListView(LoginRequiredMixin, generic.View):
    def get(self, request):
        qs = BalanceSheet.objects.filter(user=request.user.id).select_related('cheque')
        debits = qs.filter(transaction_type='debt')
        credits = qs.filter(transaction_type='credit')

        context = {
            'debits': debits,
            'credits': credits,
        }
        return render(request, 'account_base/balance_list.html', context)

# def edit_account(request, pk):
#     if request.method == 'POST':
#         try:
#             account = AccountsClass.objects.get(pk=pk)
#             account.name = request.POST.get('name')
#             account.save()
#             return JsonResponse({'success': True})
#         except AccountsClass.DoesNotExist:
#             return JsonResponse({'success': False, 'error': 'حساب یافت نشد'})

def edit_account(request, pk):
    account = get_object_or_404(AccountsClass, pk=pk)
    name = request.POST.get('name')
    if name:
        account.name = name
        account.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'نام خالی است'})

def delete_account(request, pk):
    if request.method == 'POST':
        try:
            account = AccountsClass.objects.get(pk=pk)
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
        qs = BalanceSheet.objects.filter(user=request.user.id)
        debits = qs.filter(transaction_type='debt')
        credits = qs.filter(transaction_type='credit')

        context = {
            'debits': debits,
            'credits': credits,
        }
        return render(request, 'account_base/balance_list.html', context)

def filter_credit_balance(request):
    credits = BalanceSheet.objects.filter(
        Q(user=request.user.id),
        Q(transaction_type='credit'),
    )

    account_name = request.GET.get('account_name')
    amount = request.GET.get('amount')
    balance_id = request.GET.get('balance_id')
    document_id = request.GET.get('document_id')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if balance_id:
        credits = credits.filter(id = int(balance_id))
    if document_id:
        credits = credits.filter(document_id = document_id)
    if created_at_from:
        credits = credits.filter(date_created__gte=created_at_from)
    if created_at_to:
        credits = credits.filter(date_created__lte=created_at_to)
    if amount:
        credits = credits.filter(amount=amount)
    if description:
        credits = credits.filter(description__contains=description)
    if account_name:
        credits = credits.filter(account__name__contains=account_name)
    print(credits)

    html = render_to_string('partials/credit_balance.html', {'credits': credits})
    return JsonResponse({'html': html})


def filter_debit_balance(request):
    debits = BalanceSheet.objects.filter(
        Q(user=request.user.id),
        Q(transaction_type='debt'),
    )
    print(debits)


    account_name = request.GET.get('account_name')
    amount = request.GET.get('amount')
    balance_id = request.GET.get('balance_id')
    document_id = request.GET.get('document_id')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if balance_id:
        debits = debits.filter(id = int(balance_id))
    if document_id:
        debits = debits.filter(document_id = document_id)
    if created_at_from:
        if created_at_from == created_at_to:
            debits = debits.filter(date_created__exact=created_at_from)
        else:
            debits = debits.filter(date_created__gte=created_at_from)
    if created_at_to:
        if created_at_from == created_at_to:
            debits = debits.filter(date_created__exact=created_at_to)
        else:
            debits = debits.filter(date_created__lte=created_at_to)
    if amount:
        debits = debits.filter(mount=amount)
    if description:
        debits = debits.filter(description__contains=description)
    if account_name:
        debits = debits.filter(account__name__contains=account_name)
    print(debits)

    html = render_to_string('partials/debit_balance.html', {'debits': debits})
    return JsonResponse({'html': html})