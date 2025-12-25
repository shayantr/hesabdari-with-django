import json
import time
import uuid
from collections import namedtuple
from urllib.parse import urlencode

import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, DatabaseError
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST

from hesabdari.apps.accounting.forms import DocumentForm, BalanceSheetForm, CashierChequeForm
from hesabdari.apps.accounting.models import BalanceSheet, Document
from hesabdari.apps.accounting.utils.combined_forms import CombinedForm, PostCombinedForm
from hesabdari.apps.accounting.utils.dates import add_month_to_jalali_date
from hesabdari.apps.accounting.utils.prefix_extractor import extract_all_prefixes
from hesabdari.apps.accounting.utils.tokens import get_tokens


@login_required
@require_POST
def delete_document(request, pk):
    try:
        document = get_object_or_404(Document.objects.prefetch_related(
            'items__cheque__balance_sheet'
        ), pk=pk, user=request.user)
    except Document.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "سند مورد نظر یافت نشد یا به شما تعلق ندارد."
        }, status=404)

    # checks if any balance is false
    if document.items.filter(is_active=False).exists():
        return JsonResponse({
            "success": False,
            "error": "به دلیل وجود تراکنش غیر فعال، امکان حذف این سند وجود ندارد."
        })

    # find all cheques in document
    cheque_ids = document.items.filter(
        cheque__isnull=False
    ).values_list('cheque_id', flat=True)

    if cheque_ids:
        last_inactive = (
            BalanceSheet.objects
            .filter(cheque_id__in=cheque_ids, is_active=False)
            .values('cheque_id')
            .annotate(last_id=Max('id'))
        )
        last_ids = [item['last_id'] for item in last_inactive]
        if last_ids:
            BalanceSheet.objects.filter(id__in=last_ids).update(is_active=True)
    next_url = request.GET.get('next')
    # delete document
    document.delete()
    if next_url:
        return JsonResponse({'success': True, "redirect_url": next_url})
    else:
        return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")})

@login_required
def createbalancesheet(request):
    if request.method == "GET":
        tokens = get_tokens(request.session)
        token = str(uuid.uuid4())
        tokens[token] = time.time()
        request.session["form_tokens"] = tokens
        document_instance = DocumentForm(
            initial={'user': request.user, 'date_created': request.GET.get('date_created')})
        context = {
            'all_balanceforms': [],
            'all_chequeforms': [],
            'document_instance': document_instance,
            'form_token': token,
            'enable_date_check': True,
        }
        return render(request, 'account_base/create-document.html', context)
    all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
    document_instance = DocumentForm(request.POST or None, initial={'user': request.user})
    all_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i in
                        all_prefixes]
    all_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]
    if request.method == "POST":
        tokens = get_tokens(request.session)
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
                return JsonResponse({
                    "success": False,
                    "errors": render_to_string("partials/errors.html", {"form": balance, 'err_id': balance.prefix},
                                               request=request)
                })

        if not document_instance.is_valid():
            return JsonResponse({'success': False, 'errors': document_instance.errors}, )

        if all_forms_valid:
            d = document_instance.save(commit=False)
            for balance in all_balanceforms:
                if balance.cleaned_data.get('transaction_type') == "debt":
                    all_debt += balance.cleaned_data.get('amount') or 0
                elif balance.cleaned_data.get('transaction_type') == "credit":
                    all_credit += balance.cleaned_data.get('amount') or 0

            if all_credit != all_debt:
                return JsonResponse({'success': False, 'errors': 'مجموع بدهکاری و بستانکاری برابر نیست.'}, )
            else:
                try:
                    with transaction.atomic():
                        d.save()
                        for balance, cheque in zip(all_balanceforms, all_chequeforms):
                            b = balance.save(commit=False)
                            if cheque.cleaned_data.get('name'):
                                c = cheque.save()
                                b.cheque = c
                            b.document = d
                            b.save()
                except DatabaseError as e:  # exception for unexpected errors
                    return JsonResponse({
                        "success": False,
                        "errors": "مشکلی در ذخیره اطلاعات پیش آمد. دوباره تلاش کنید."
                        # اگر خواستی برای دیباگ:  f"خطا: {str(e)}"
                    }, status=500)
                try:
                    tokens.pop(token, None)
                    request.session["form_tokens"] = tokens
                    url = reverse('create-document')
                    date_created = request.POST.get('date_created')
                    redirect_url = f"{url}?{urlencode({'date_created': date_created})}"
                    return JsonResponse({'success': True, "redirect_url": redirect_url})
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

        form_balance = BalanceSheetForm(prefix=f'{uniqueid}-new-balance',
                                        initial={'transaction_type': transaction_type, 'user': request.user.id})
        if transaction_type == 'debt':
            form_cheque = CashierChequeForm(prefix=f'{uniqueid}-new-cheque',
                                            initial={'user': request.user.id, 'cheque_type': 'دریافتنی'})
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance, 'form_cheque': form_cheque,
                                          'transaction_type': transaction_type, 'uniqueid': uniqueid})
        else:
            form_cheque = CashierChequeForm(prefix=f'{uniqueid}-new-cheque',
                                            initial={'user': request.user.id, 'cheque_type': 'پرداختنی'})
            form_html = render_to_string('account_base/form_fragment.html',
                                         {'form_balance': form_balance, 'form_cheque': form_cheque,
                                          'transaction_type': transaction_type, 'uniqueid': uniqueid})
        return JsonResponse({'form_html': form_html, 'datease': datease})

class UpdateBalanceView(LoginRequiredMixin, generic.View):

    def get(self, request, pk):
        document = get_object_or_404(Document, pk=pk)
        document_form = DocumentForm(request.POST or None, instance=document)

        balancesheets = (
            BalanceSheet.objects
            .filter(document=document)
            .select_related("account", "cheque__account")  # FK ها
            .prefetch_related("cheque__balance_sheet")  # reverse relation
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
            'enable_date_check': True,
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
            .select_related("account", "cheque__account")  # FK ها
            .prefetch_related("cheque__balance_sheet")  # reverse relation
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

class ChangeStatusCheque(generic.View):
    def get(self, request, pk):
        balancesheet = get_object_or_404(BalanceSheet, id=pk, user=request.user, is_active=True)
        document = DocumentForm(request.POST or None, initial={'user': request.user, 'date_created': balancesheet.cheque.maturity_date})
        combined_forms = []
        locked = True
        combined_form = namedtuple('combined_form',
                                   ['uniqueid', 'form_balance', 'form_cheque', 'chequeid', 'bank_str',
                                    'balance_id', 'account_str', 'locked'])
        if balancesheet.transaction_type == 'debt':
            balance_forms = BalanceSheetForm(prefix=f"old-update-cheque-update-balance",
                                             initial={"user": request.user, "transaction_type": 'credit',
                                                      'amount': balancesheet.amount, 'account': balancesheet.account
                                                 , 'description': balancesheet.description, 'previous_cheque_status': balancesheet.cheque.cheque_status
                                                      })
        else:
            balance_forms = BalanceSheetForm(prefix=f"old-update-cheque-update-balance",
                                             initial={"user": request.user, "transaction_type": 'debt',
                                                      'amount': balancesheet.amount, 'account': balancesheet.account
                                                 , 'description': balancesheet.description, 'previous_cheque_status': balancesheet.cheque.cheque_status
                                                      })
        balance_id = 'old-update-balance'
        # balancesheet.cheque.cheque_status = 'وصولی'
        cheque_forms = CashierChequeForm(prefix=f"old-update-cheque-update-cheque", instance=balancesheet.cheque)
        chequeid = balancesheet.cheque.id
        bank_str = balancesheet.cheque.account.__str__()
        combined_forms.append(
            combined_form("old-update-cheque", balance_forms, cheque_forms, chequeid, bank_str, balance_id,
                          balancesheet.account, locked))
        context = {
            'document_instance': document,
            'combined_forms': combined_forms,
        }
        return render(request, "account_base/create-document.html", context)

    def post(self, request, pk):
        document = DocumentForm(request.POST or None)
        balancesheet = BalanceSheet.objects.filter(id=pk, user=request.user, is_active=True).last()
        next_url = request.GET.get('next', reverse('cheque-lists-view'))
        all_credit = 0
        all_debt = 0
        all_valid = True
        user = request.user
        balanceCheqe = BalanceSheetForm(request.POST, request.FILES, prefix=f"old-update-cheque-update-balance")
        update_Cheqe = CashierChequeForm(request.POST or None, prefix=f"old-update-cheque-update-cheque",
                                         instance=balancesheet.cheque)
        if not balanceCheqe.is_valid() or not update_Cheqe.is_valid() or not document.is_valid():
            all_valid = False
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
