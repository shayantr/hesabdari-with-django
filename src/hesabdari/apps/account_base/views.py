from collections import namedtuple
from itertools import zip_longest

import jdatetime
import uuid
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.views import generic

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


def createbalancesheet(request):
    all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
    print(request.user)
    document = DocumentForm(request.POST or None, initial={'user':request.user.is_authenticated})
    all_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i in all_prefixes]
    all_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]
    if request.method == "POST":
        all_credit = 0
        all_debt = 0
        all_forms_valid = True

        if document.is_valid():
            document_instance = document.save(commit=False)

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
                    return JsonResponse({'success': True, "redirect_url": reverse("test")},)

    context = {
        'documentform': document,
        'all_balanceforms': all_balanceforms,
        'all_chequeforms': all_chequeforms,
    }

    return render(request, 'account_base/test.html', context)


class GetFormFragmentView(generic.View):
    def post(self, request):
        if request.POST.get('maturity_date'):
            datease = request.POST.get('maturity_date')
            datease = str(add_month_to_jalali_date(jdatetime.date.fromisoformat(datease)))
        else:
            datease = ''
        uniqueid = str(uuid.uuid1())[:4]
        transaction_type = request.POST.get('transaction_type')
        form_cheque = CashierChequeForm(prefix=f'{uniqueid}-new-cheque', initial={'user':User.objects.get(id=1)})
        form_balance = BalanceSheetForm(prefix=f'{uniqueid}-new-balance', initial={'transaction_type': transaction_type, 'user':User.objects.get(id=1)})
        if transaction_type == 'debt':
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance,'form_cheque':form_cheque,
                                          'transaction_type':transaction_type, 'uniqueid':uniqueid})
        else:
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance, 'form_cheque': form_cheque,
                                          'transaction_type': transaction_type, 'uniqueid':uniqueid})
        return JsonResponse({'form_html': form_html, 'datease':datease })

def build_tree(node):
    return {
        'id': node.id,
        'name': node.name,
        'children': [build_tree(child) for child in node.get_children()]
    }

class AccountsView(generic.View):
    def get(self, request):
        list_accounts = AccountsClass.get_tree()
        accountform = AccountsForm()
        tree_data = [build_tree(root) for root in AccountsClass.get_root_nodes()]


        form_html = render_to_string('account_base/accounts.html',
                                     {'list_accounts': list_accounts, "accountform":accountform})
        return JsonResponse({'form_html': form_html, 'tree_data':tree_data})

    def post(self, request):
        list_accounts = AccountsClass.objects.all()
        print(list_accounts)
        context = {
            'list_accounts': list_accounts
        }
        return JsonResponse({'list_accounts': list_accounts })

class CreateAccounts(generic.View):
    def post(self, request):
        accountform = AccountsForm(request.POST or None)
        if accountform.is_valid():
            account = accountform.save()
            parent = AccountsClass.get_parent(account) or None
            return JsonResponse({
                'success': True,
                'id': account.id,
                'name': account.name,
                'parent_id': parent.id if parent else None
            })

        return JsonResponse({'success': False, 'errors': accountform.errors})
def extract_all_update_prefixes(post_data, file_data):
    prefixes = set()
    combined_keys = list(post_data.keys()) + list(file_data.keys())

    for key in combined_keys:
        if '-update' in key:
            prefix = key.split('-')[0]
            prefixes.add(prefix)
    return prefixes
class UpdateBalanceView(generic.View):
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
        return render(request, "account_base/test.html", context)
    def post(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        all_credit = 0
        all_debt = 0
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
                        c = item.form_cheque.save()
                        b.cheque = c
                    b.document = document
                    b.save()
                #save new balance and cheque forms
                for balance, cheque in zip(all_new_balanceforms, all_new_chequeforms):
                    b = balance.save(commit=False)
                    if cheque.cleaned_data.get('name'):
                        c = cheque.save()
                        b.cheque = c
                    b.document = document
                    b.save()
                return JsonResponse({'success': True, "redirect_url": reverse("test")}, )

        context = {
            'documentform': document,
            'all_balanceforms': all_new_balanceforms,
            'all_chequeforms': all_new_chequeforms,
            'form_action_url': reverse('UpdateBalanceView', args=[pk])
        }

        return render(request, 'account_base/test.html', context)

# def deletechequeview(request, pk):
#     if request.method == 'POST':
#         cheque
