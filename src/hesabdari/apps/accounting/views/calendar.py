from datetime import datetime

import jdatetime
from django.http import JsonResponse
from django.shortcuts import render

from hesabdari.apps.accounting.models import BalanceSheet


def calendar_page(request):
    today = jdatetime.date.today()
    current_year = today.year
    print(jdatetime.j_days_in_month)
    print(jdatetime.date)

    # ۱۰۰ سال قبل تا ۵ سال آینده
    start_year = current_year - 100
    end_year = current_year + 5

    # ایجاد لیست سال‌ها
    years = list(range(start_year, end_year + 1))
    print(years)
    return render(request, 'account_base/calendar.html')
def all_events(request):
    events = BalanceSheet.objects.filter(cheque__isnull=False).prefetch_related('cheque')

    event_list = []
    daily_totals = {}
    for e in events:
        g_date = e.cheque.maturity_date.togregorian()
        key = g_date.isoformat()
        if key not in daily_totals:
            daily_totals[key] = 0
        daily_totals[key] += e.amount
    for date, total in daily_totals.items():
        event_list.append({
            'title': 'چک',
            "start": date,
            "allDay": True

        })

    return JsonResponse(event_list, safe=False)

def cheques_of_day(request):
    g_date = datetime.strptime(
        request.GET['date'], "%Y-%m-%d"
    ).date()
    j_date = jdatetime.date.fromgregorian(date=g_date)
    cheques = BalanceSheet.objects.filter(cheque__isnull=False, cheque__maturity_date=j_date).prefetch_related('cheque')
    return JsonResponse({
        "date": str(j_date),
        "total": sum(c.amount for c in cheques),
        "items": [
            {
                "name": c.description or "—",
                "amount": c.amount
            }
            for c in cheques
        ]
    })