import json
import time
import uuid
from collections import namedtuple
from urllib.parse import urlencode

import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST

from hesabdari.apps.accounting.forms import DocumentForm, BalanceSheetForm, CashierChequeForm
from hesabdari.apps.accounting.models.balancesheet import BalanceSheet
from hesabdari.apps.accounting.models.document import Document
from hesabdari.apps.accounting.selectors.document import get_document_balances_for_update, \
    get_document_balances_for_change_status
from hesabdari.apps.accounting.services.cheques.change_cheque_status_service import ChangeChequeStatusService
from hesabdari.apps.accounting.services.document.document_service import DocumentService
from hesabdari.apps.accounting.services.document.update_document import UpdateDocumentService
from hesabdari.apps.accounting.utils.combined_forms import CombinedForm
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

        # call service
        service = DocumentService(
            document_instance,
            all_balanceforms,
            all_chequeforms,
        )
        success, result = service.execute()
        if not success:
            if result["type"] == "row":
                print(result["form"], result["err_id"])
                html = render_to_string(
                    "partials/errors.html",
                    {
                        "form": result["form"],
                        "err_id": result["err_id"],
                    },
                    request=request
                )
                return JsonResponse({
                    "success": False,
                    "errors": html
                })
            return JsonResponse(
                {
                    "success": success,
                    "errors": result,
                }
            )
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
        document = get_object_or_404(Document, pk=pk, user=request.user)
        document_form = DocumentForm(request.POST or None, instance=document)

        balancesheets = get_document_balances_for_update(document, request.user)

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
        balance_sheets = get_document_balances_for_update(document, user)
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

        service = UpdateDocumentService(document, balance_sheets, document_form, new_balance_forms, new_cheque_forms, deleted_ids, user, request.POST, request.FILES)
        all_valid, errors = service.execute()

        if not all_valid:
            return JsonResponse({'success': False, 'errors': errors})
        else:
            if next_url:
                return JsonResponse({'success': True, "redirect_url": next_url})
            else:
                return JsonResponse({'success': True, "redirect_url": reverse("balance_lists")})


