import json
from collections import namedtuple
from itertools import zip_longest
from lib2to3.fixes.fix_input import context

import jdatetime
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Prefetch
from django.db.transaction import commit
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
    document_instance = DocumentForm(request.POST or None, initial={'user':request.user})
    # document_instance = Document(user=request.user)
    all_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i in all_prefixes]
    all_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]
    if request.method == "POST":
        all_credit = 0
        all_debt = 0
        all_forms_valid = True



        for balance, cheque in zip(all_balanceforms, all_chequeforms):
            if not balance.is_valid() or not cheque.is_valid():
                all_forms_valid = False
        if not document_instance.is_valid():
            all_forms_valid = False

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
                print(document_instance)
                d.save()
                document_instance.save()
                for balance, cheque in zip(all_balanceforms, all_chequeforms):
                    b = balance.save(commit=False)
                    if cheque.cleaned_data.get('name'):
                        c = cheque.save()
                        b.cheque = c
                    b.document = d
                    b.save()
                return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")},)

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


def account_report(request):
    return render(request, 'account_base/accounts-report.html')
class AccountsView(generic.View):
    def get(self, request):
        def serialize_node(node, net_total):
            return {
                'id': str(node.id),
                'text': node.name,
                'parent': str(node.parent.id) if node.parent else '#',
                'li_attr': {'data-net-total': net_total},
            }

        accounts = AccountsClass.objects.filter(user=request.user).prefetch_related(
            Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user)))
        data= []
        for account in accounts:
            descendants = account.get_descendants(include_self=True)
            total_debtor = 0
            total_creditor = 0
            for descendant in descendants:
                for bs in descendant.balance_sheets.all():
                    if bs.amount:
                        if bs.transaction_type == 'debt':
                            total_debtor += bs.amount
                        elif bs.transaction_type == 'credit':
                            total_creditor += bs.amount

            net_total = total_creditor - total_debtor

            data.append(serialize_node(account, net_total))

        # data = [serialize_node(acc) for acc in accounts]
        form_html = render_to_string('account_base/accounts.html', {
            'uniqueid': request.GET.get('uid', 'default')
        })
        return JsonResponse({'form_html': form_html, 'data': data})

class AccountReportDetails(generic.View):
    def get(self, request, pk):
        parent_account = get_object_or_404(AccountsClass, pk=pk, user=request.user)
        descendants = (parent_account.get_descendants(include_self=True).prefetch_related(Prefetch('balance_sheets', queryset=BalanceSheet.objects.filter(user=request.user))))
        qs = []
        id_lists = []
        for descendant in descendants:
            for balance in descendant.balance_sheets.all():
                qs.append(balance)
                id_lists.append(balance.id)
        context = {
            'balance_lists':qs,
            'id_lists': id_lists
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


class UpdateBalanceView(LoginRequiredMixin, generic.View):
    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        document_instance = DocumentForm(request.POST or None, instance=document)
        balancesheet = BalanceSheet.objects.filter(document=document)
        combined_forms = []
        combined_form = namedtuple('combined_form', ['uniqueid', 'form_balance', 'form_cheque', 'chequeid', 'account_str', 'bank_str', 'balance_id'])
        for i in balancesheet:
            balance_forms = BalanceSheetForm(prefix=f"{i.id}-update-balance", instance=i)
            balance_id = i.id
            account_str = i.account.__str__()
            bank_str = "----"
            chequeid= None
            if i.cheque:
                cheque_forms = CashierChequeForm(prefix=f"{i.id}-update-cheque", instance=i.cheque)
                chequeid = i.cheque.id
                bank_str=i.cheque.account.__str__()
            else:
                cheque_forms = CashierChequeForm(prefix=f"{i.id}-update-cheque")
            combined_forms.append(combined_form(i.id, balance_forms, cheque_forms, chequeid, account_str, bank_str, balance_id))
        context = {
            'combined_forms': combined_forms,
            'document_id': document.id,
            'document_instance': document_instance,
        }
        return render(request, "account_base/create-document.html", context)
    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        document_instance = DocumentForm(request.POST or None, instance=document)
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
        if not document_instance.is_valid():
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
                    document_instance.save()
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
                    document_instance.save()

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

    html = render_to_string('partials/credit_cheques.html', {'credits': credits})
    return JsonResponse({'html': html})


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
def delete_balance(request):
    try:
        balance_id = request.POST.get('balance_id')
        print(balance_id)
        balance = BalanceSheet.objects.get(user=request.user, pk=balance_id)
        print(balance)
        print('balance')
        balance.delete()
        return JsonResponse({'success': True})
    except BalanceSheet.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'سند پیدا نشد'})

@login_required
@require_POST
def delete_document(request, pk):
    try:
        document = Document.objects.get(pk=pk, user=request.user)
        document.delete()
        return redirect(reverse('balance_lists'))
    except Document.DoesNotExist:
        return redirect(reverse('delete_document', pk))


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
        qs = BalanceSheet.objects.filter(user=request.user.id).select_related('cheque')
        context = {
            'balance_lists': qs,
        }
        return render(request, 'account_base/balance_list.html', context)


def filter_balance(request):
    if request.GET.get('id_lists'):
        id_lists_json = request.GET.get('id_lists', '[]')
        id_lists = json.loads(id_lists_json)
        id_lists = [int(i) for i in id_lists]
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id, id__in=id_lists),
        )
    else:
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id),
        )

    account_name = request.GET.get('account_name')
    amount = request.GET.get('amount')
    balance_id = request.GET.get('balance_id')
    document_id = request.GET.get('document_id')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')

    if balance_id:
        qs = qs.filter(id = int(balance_id))
    if document_id:
        qs = qs.filter(document_id = document_id)
    if created_at_from:
        if created_at_from == created_at_to:
            qs = qs.filter(date_created__exact=created_at_from)
        else:
            qs = qs.filter(date_created__gte=created_at_from)
    if created_at_to:
        if created_at_from == created_at_to:
            qs = qs.filter(date_created__exact=created_at_to)
        else:
            qs = qs.filter(date_created__lte=created_at_to)
    if amount:
        qs = qs.filter(amount=amount)
    if description:
        qs = qs.filter(description__contains=description)
    if account_name:
        qs = qs.filter(account__name__contains=account_name)

    html = render_to_string('partials/search_balance.html', {'balance_lists': qs})
    return JsonResponse({'html': html})

class ChangeStatusCheque(generic.View):
    def get(self, request, pk):
        balancesheet = BalanceSheet.objects.get(id=pk, user=request.user)
        combined_forms = []
        combined_form = namedtuple('combined_form',
                                   ['uniqueid', 'form_balance', 'form_cheque', 'chequeid', 'bank_str',
                                    'balance_id'])
        if balancesheet.transaction_type == 'debt':
            balance_forms = BalanceSheetForm(prefix=f"change-cheque-balance", initial={"transaction_type":'credit', 'amount':balancesheet.amount})
        else:
            balance_forms = BalanceSheetForm(prefix=f"change-cheque-balance", initial={"transaction_type": 'debt', 'amount':balancesheet.amount})
        balance_id = 'old-update-balance'
        cheque_forms = CashierChequeForm(prefix=f"change-cheque", instance=balancesheet.cheque)
        chequeid = balancesheet.cheque.id
        bank_str = balancesheet.cheque.account.__str__()
        combined_forms.append(
                combined_form("old-update-cheque", balance_forms, cheque_forms, chequeid, bank_str, balance_id))
        context = {
            'combined_forms': combined_forms,
        }
        return render(request, "account_base/create-document.html", context)
    def post(self, request, pk):
        document = Document(user=request.user)
        balancesheet = BalanceSheet.objects.get(id=pk, user=request.user)
        all_credit = 0
        all_debt = 0
        all_valid = True
        combined_forms = []
        user = request.user
        balanceCheqe = BalanceSheetForm(request.POST, request.FILES, prefix=f"change-cheque-balance")
        update_Cheqe = CashierChequeForm(request.POST or None, prefix=f"change-cheque-balance", instance=balancesheet.cheque)
        if not balanceCheqe.is_valid() or not update_Cheqe.is_valid():
            all_valid = False
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
                for item in combined_forms:
                    b = item.form_balance.save(commit=False)
                    if item.form_cheque.cleaned_data.get('name'):
                        c = item.form_cheque.save(commit=False)
                        c.user = user
                        c.save()
                        b.cheque = c
                    b.document = document
                    b.save()
                # save new balance and cheque forms
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




