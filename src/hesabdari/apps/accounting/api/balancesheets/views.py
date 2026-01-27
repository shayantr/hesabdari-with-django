import json
import urllib

import jdatetime
import openpyxl
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Case, When, IntegerField
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import generic

from hesabdari.apps.accounting.models.accounts import AccountsClass
from hesabdari.apps.accounting.models.balancesheet import BalanceSheet


class BalanceListView(LoginRequiredMixin, generic.View):
    def get(self, request):
        context = {}
        return render(request, 'account_base/balance_list.html', context)

def _filter_balance_handler(request):
    current_day = jdatetime.date.today()
    if request.GET.get('id_lists'):
        id_lists_json = request.GET.get('id_lists', '[]')
        id_lists = json.loads(id_lists_json)
        id_lists = [int(i) for i in id_lists]
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id, id__in=id_lists),
        ).select_related('document').prefetch_related('document__items__account')
    else:
        qs = BalanceSheet.objects.filter(
            Q(user=request.user.id)).select_related('document').prefetch_related('document__items__account')
    debt_div = request.GET.get('debt_div')
    credit_div = request.GET.get('credit_div')
    result_div = request.GET.get('result_div')
    account_id = request.GET.get('account_id')
    amount = request.GET.get('amount')
    balance_id = request.GET.get('balance_id')
    document_id = request.GET.get('document_id')
    created_at_from = request.GET.get('created_at_from')
    created_at_to = request.GET.get('created_at_to')
    description = request.GET.get('description')
    page = request.GET.get('page')
    debt_condition = {'transaction_type': 'debt'}
    credit_condition = {'transaction_type': 'credit'}
    if debt_div == 'clicked':
        qs = qs.filter(transaction_type='debt')
    if credit_div == 'clicked':
        qs = qs.filter(transaction_type='credit')
    if balance_id:
        qs = qs.filter(id=int(balance_id))
    if document_id:
        qs = qs.filter(document_id=document_id)
    if amount:
        qs = qs.filter(amount=amount)
    if description:
        qs = qs.filter(description__contains=description)
    if account_id:
        accounts = AccountsClass.objects.get(id=account_id)
        accounts = accounts.get_descendants(include_self=True)
        qs = qs.filter(account__in=accounts)
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

    balance_list = []
    running_balance = pre_total_debt - pre_total_credit
    for item in qs.order_by('document__date_created', 'id'):
        doc = item.document
        if item.transaction_type == 'debt':  # بدهکاری
            running_balance += item.amount
        elif item.transaction_type == 'credit':  # بستانکاری
            running_balance -= item.amount
        item.running_balance = running_balance
        people = {i.account.name for i in doc.items.all() if item.transaction_type != i.transaction_type}
        item.people = people
        balance_list.append(item)
    balance_list = list(reversed(balance_list))
    return balance_list, page, total_credit, total_debt, pre_total_credit, pre_total_debt, sum_debt, sum_credit

def filter_balance(request):
    balance_list, page,total_credit, total_debt, pre_total_credit, pre_total_debt, sum_debt, sum_credit = _filter_balance_handler(request)

    paginator = Paginator(balance_list, 20)
    current_page = paginator.get_page(page)
    html = render_to_string('partials/search_balance.html', {'balance_lists': current_page})
    return JsonResponse(
        {
            'html': html,
            'total_debt': total_debt,
            'total_credit': total_credit,
            'sum_debt': sum_debt,
            'sum_credit': sum_credit,
            'pre_total_credit': pre_total_credit,
            'pre_total_debt': pre_total_debt,
            'has_next': current_page.has_next(),
            'next_page_number': current_page.next_page_number() if current_page.has_next() else None,})



def csv_balance(request):
    balance_list, page, total_credit, total_debt, pre_total_credit, pre_total_debt, sum_debt, sum_credit = _filter_balance_handler(request)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'balance_sheet_csv'
    ws.append(['حساب',"نوع حساب", "مبلغ", "صاحب چک", "طرف حساب", "مانده", "توضیحات"])
    for item in balance_list:
        print(item.people)
        ws.append([
            item.id,
            item.transaction_type,
            item.amount,
            item.account.name,
            ",".join(item.people),
            item.running_balance,
            item.description or "",


        ])
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    today = str(jdatetime.date.today())
    filename = f"balance_{today}.xlsx"
    filename = urllib.parse.quote(filename)
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{filename}"
    wb.save(response)
    return response




