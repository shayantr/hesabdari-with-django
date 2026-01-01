import urllib

import jdatetime
import openpyxl
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Sum, Case, When, IntegerField
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import generic
from django.views.decorators.http import require_POST

from hesabdari.apps.accounting.models import CashierCheque, BalanceSheet


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
    qs = BalanceSheet.objects.filter(
        user=request.user.id,
        cheque__cheque_type=cheque_type,
        cheque__isnull=False,
        is_active=True
    ).select_related('cheque').only(
        'cheque__name',
        'cheque__cheque_status',
        'cheque__maturity_date',
        'amount',
        'description',
        'cheque__cheque_type'
    ).order_by("cheque__maturity_date")

    # فیلترها
    name = request.GET.get('cheque_name')
    debt_div = request.GET.get('receivable_debt_div')
    credit_div = request.GET.get('receivable_credit_div')
    status = request.GET.get('cheque_status')
    amount = request.GET.get('amount')
    due_date_from = request.GET.get('due_date_from')
    due_date_to = request.GET.get('due_date_to')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')
    page = request.GET.get('page', 1)

    highlight = f"{transaction}_result_div"

    if due_date_from:
        qs = qs.filter(cheque__maturity_date__gte=due_date_from).order_by("cheque__maturity_date")
    if due_date_to:
        qs = qs.filter(cheque__maturity_date__lte=due_date_to).order_by("cheque__maturity_date")
    if created_at_from:
        qs = qs.filter(document__date_created__gte=created_at_from).order_by(
            '-document__date_created')
    if created_at_to:
        qs = qs.filter(document__date_created__lte=created_at_to).order_by('-document__date_created')
    if amount:
        qs = qs.filter(amount=amount)
    if status:
        qs = qs.filter(cheque__cheque_status=status)
    if name:
        qs = qs.filter(cheque__name__icontains=name)
    if description:
        qs = qs.filter(description__contains=description)
    if debt_div:
        qs = qs.filter(transaction_type='debt')
        highlight = f"{transaction}_debt_div"
    if credit_div:
        qs = qs.filter(transaction_type='credit')
        highlight = f"{transaction}_credit_div"
    # محاسبه جمع‌ها
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
    return qs, highlight, aggregates, page

def filter_receivable_cheques(request):
    receivables, highlight, aggregates, page = _filter_cheques(request, "دریافتنی", "receivable")

    paginator = Paginator(receivables, 20)
    current_page = paginator.get_page(page)


    receivables_debt_amount = aggregates['debt'] or 0
    receivables_credit_amount = aggregates['credit'] or 0

    # رندر لیست به html
    html = render_to_string('partials/receivable_cheques.html', {'receivables': current_page})
    return JsonResponse({
        'html': html,
        'receivables_debt_amount': receivables_debt_amount,
        'receivables_credit_amount': receivables_credit_amount,
        'has_next': current_page.has_next(),
        'next_page_number': current_page.next_page_number() if current_page.has_next() else None,
        'highlight': highlight
    })


def filter_payable_cheques(request):
    payables, highlight, aggregates, page = _filter_cheques(request, "پرداختنی", "payable")
    paginator = Paginator(payables, 20)
    current_page = paginator.get_page(page)

    payables_debt_amount = aggregates['debt'] or 0
    payables_credit_amount = aggregates['credit'] or 0

    # رندر لیست به html
    html = render_to_string('partials/payable_cheques.html', {'payables': current_page})

    return JsonResponse({
        'html': html,
        'payables_debt_amount': payables_debt_amount,
        'payables_credit_amount': payables_credit_amount,
        'has_next': current_page.has_next(),
        'next_page_number': current_page.next_page_number() if current_page.has_next() else None,
        "highlight": highlight,
    })




def csv_cheque(request):
    cheque_type = request.GET.get('tab') or 'recivable'
    if cheque_type == 'recivable':
        cheque_type = 'دریافتنی'
    elif cheque_type == 'payable':
        cheque_type = 'پرداختنی'
    qs, highlight, aggregates, page = _filter_cheques(request, cheque_type, 'none')

    receivables_debt_amount = aggregates['debt'] or 0
    receivables_credit_amount = aggregates['credit'] or 0

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = cheque_type
    ws.append(['تاریخ سررسید', "مبلغ", "صاحب چک", "در وجه", "بانک", 'شماره چک', 'وضعیت چک', "توضیحات"])
    for item in qs:
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

