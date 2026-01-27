from django.core.paginator import Paginator
from django.db.models import Sum, Case, When, IntegerField

from hesabdari.apps.accounting.models.balancesheet import BalanceSheet


class ChequeSelector:
    def __init__(self, user, cheque_type):
        self.qs = BalanceSheet.objects.filter(
            user=user,
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
        )
        self.highlight_suffix = None
        self.filters = {}

    def apply_filters(self, filters: dict):
        self.filters = filters
        if filters.get("due_date_from"):
            self.qs = self.qs.filter(cheque__maturity_date__gte=filters["due_date_from"])
        if filters.get("due_date_to"):
            self.qs = self.qs.filter(cheque__maturity_date__lte=filters["due_date_to"])
        if filters.get("created_at_from"):
            self.qs = self.qs.filter(document__date_created__gte=filters["created_at_from"])
        if filters.get("created_at_to"):
            self.qs = self.qs.filter(document__date_created__lte=filters["created_at_to"])
        if filters.get("amount"):
            self.qs = self.qs.filter(amount=filters["amount"])
        if filters.get("cheque_status"):
            self.qs = self.qs.filter(cheque__cheque_status=filters["cheque_status"])
        if filters.get("cheque_name"):
            self.qs = self.qs.filter(cheque__name__icontains=filters["cheque_name"])
        if filters.get("description"):
            self.qs = self.qs.filter(description__icontains=filters["description"])
        if filters.get("receivable_debt_div") or filters.get("payable_debt_div"):
            self.qs = self.qs.filter(transaction_type='debt')
            self.highlight_suffix = 'debt_div'
        if filters.get("receivable_credit_div") or filters.get("payable_credit_div"):
            self.qs = self.qs.filter(transaction_type='credit')
            self.highlight_suffix = 'credit_div'

        return self

    def get_queryset(self):
        return self.qs

    def order(self):
        if self.filters.get('created_at_to') or self.filters.get('created_at_from'):
            self.qs = self.qs.order_by('-id','-document__date_created')
        else:
            self.qs = self.qs.order_by('-id','cheque__maturity_date')

    def aggregate_totals(self):
        return self.qs.aggregate(
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
    def paginate(self, page, per_page=20):
        paginator = Paginator(self.qs, per_page)
        return paginator.get_page(page)