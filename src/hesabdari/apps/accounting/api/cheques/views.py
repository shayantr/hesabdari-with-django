import urllib
from collections import namedtuple

import jdatetime
import openpyxl
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST

from hesabdari.apps.accounting.forms import DocumentForm, BalanceSheetForm, CashierChequeForm
from hesabdari.apps.accounting.models.balancesheet import BalanceSheet
from hesabdari.apps.accounting.models.cheque import CashierCheque
from hesabdari.apps.accounting.selectors.cheques import ChequeSelector
from hesabdari.apps.accounting.selectors.document import get_document_balances_for_change_status
from hesabdari.apps.accounting.services.cheques.change_cheque_status_service import ChangeChequeStatusService
from hesabdari.apps.accounting.utils.prefix_extractor import extract_all_prefixes


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
        context = {}
        return render(request, 'account_base/cheque-lists.html', context)

def _filter_cheques(request, cheque_type, transaction):
    filters = request.GET.dict()
    page = request.GET.get('page', 1)
    selector = ChequeSelector(request.user, cheque_type)
    selector.apply_filters(filters).order()
    aggregates = selector.aggregate_totals()
    current_page = selector.paginate(page)

    highlight = f"{transaction}_{selector.highlight_suffix or 'result_div'}"

    return selector, current_page, highlight, aggregates

def filter_receivable_cheques(request):
    selector, current_page, highlight, aggregates = _filter_cheques(request, "دریافتنی", "receivable")
    print(CashierCheque.objects.filter(balance_sheet=None).count())
    for i in CashierCheque.objects.filter(balance_sheet=None):
        print(i.id)

    return JsonResponse({
        'html': render_to_string('partials/receivable_cheques.html', {'receivables': current_page}),
        'receivables_debt_amount': aggregates['debt'] or 0,
        'receivables_credit_amount': aggregates['credit'] or 0,
        'has_next': current_page.has_next(),
        'next_page_number': current_page.next_page_number() if current_page.has_next() else None,
        'highlight': highlight
    })


def filter_payable_cheques(request):
    selector, current_page, highlight, aggregates = _filter_cheques(request, "پرداختنی", "payable")
    return JsonResponse({
        'html': render_to_string('partials/payable_cheques.html', {'payables': current_page}),
        'payables_debt_amount': aggregates['debt'] or 0,
        'payables_credit_amount': aggregates['credit'] or 0,
        'has_next': current_page.has_next(),
        'next_page_number': current_page.next_page_number() if current_page.has_next() else None,
        'highlight': highlight
    })




def csv_cheque(request):
    cheque_type = request.GET.get('tab') or 'recivable'
    if cheque_type == 'recivable':
        cheque_type = 'دریافتنی'
    elif cheque_type == 'payable':
        cheque_type = 'پرداختنی'
    selector = ChequeSelector(request.user, cheque_type)
    selector.apply_filters(request.GET.dict()).order()
    selector = selector.get_queryset()


    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = cheque_type
    ws.append(['تاریخ سررسید', "مبلغ", "صاحب چک", "در وجه", "بانک", 'شماره چک', 'وضعیت چک', "توضیحات"])
    for item in selector:
        ws.append([
            item.cheque.maturity_date.strftime("%Y-%m-%d") if item.cheque.maturity_date else "",
            item.amount,
            item.cheque.name,
            item.cheque.in_cash,
            item.cheque.account.__str__(),
            item.cheque.Cheque_numbder,
            item.cheque.cheque_status,
            item.description or "",
        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    today = str(jdatetime.date.today())
    filename = f"{cheque_type}_cheques_{today}.xlsx"
    filename = urllib.parse.quote(filename)
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
    wb.save(response)
    return response

class ChangeStatusCheque(generic.View):
    def get(self, request, pk):
        balancesheet = get_document_balances_for_change_status(id=pk, user=request.user).get()
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
        user = request.user
        document = DocumentForm(request.POST or None)
        balancesheet = get_document_balances_for_change_status(pk, user).get()
        next_url = request.GET.get('next', reverse('cheque-lists-view'))
        balanceCheqe = BalanceSheetForm(request.POST, request.FILES, prefix=f"old-update-cheque-update-balance")
        update_Cheqe = CashierChequeForm(request.POST or None, prefix=f"old-update-cheque-update-cheque",
                                         instance=balancesheet.cheque)

        all_prefixes = extract_all_prefixes(request.POST, request.FILES) if request.method == "POST" else set()
        all_new_balanceforms = [BalanceSheetForm(request.POST, request.FILES or None, prefix=f'{i}-new-balance') for i
                                in
                                all_prefixes]
        all_new_chequeforms = [CashierChequeForm(request.POST or None, prefix=f'{i}-new-cheque') for i in all_prefixes]

        service = ChangeChequeStatusService(balancesheet, document, balanceCheqe, update_Cheqe, all_new_balanceforms, all_new_chequeforms, user)
        all_valid, errors = service.execute()
        if not all_valid:
            return JsonResponse({'success': False, 'errors': errors})

        if next_url:
            return JsonResponse({'success': True, "redirect_url": next_url}, )
        else:
            return JsonResponse({'success': True, "redirect_url": reverse("cheque-lists-view")}, )
