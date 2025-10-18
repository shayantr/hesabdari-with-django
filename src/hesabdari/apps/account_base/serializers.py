from django.db import transaction
from rest_framework import serializers

from hesabdari.apps.account_base.models import CashierCheque, BalanceSheet, Document, AccountsClass


class AccountsSerializer(serializers.ModelSerializer):
    def validate_user(self, value):
        request_user = self.context['request'].user
        if value != request_user:
            raise serializers.ValidationError("شما مجاز به استفاده از این کاربر نیستید.??????")

    class Meta:
        model = AccountsClass
        fields = '__all__'
        read_only_fields = ['user']

class CashierChequeSerializer(serializers.ModelSerializer):
    def validate_user(self, value):
        request_user = self.context['request'].user
        if value != request_user:
            raise serializers.ValidationError("شما مجاز به استفاده از این کاربر نیستید.????????")

    class Meta:
        model = CashierCheque
        fields = '__all__'
        read_only_fields = ['user']

class BalanceSheetSerializer(serializers.ModelSerializer):
    cheque = CashierChequeSerializer(required=False, allow_null=True)
    def validate_user(self, value):
        request_user = self.context['request'].user
        if value != request_user:
            raise serializers.ValidationError("شما مجاز به استفاده از این کاربر نیستید.")


    class Meta:
        model = BalanceSheet
        fields = '__all__'
        read_only_fields = ['user']

class DocumentSerializer(serializers.ModelSerializer):
    items = BalanceSheetSerializer(many=True)

    class Meta:
        model = Document
        fields = ['id', 'date_created', 'items']
        read_only_fields = ['user']

    def validate_user(self, value):
        request_user = self.context['request'].user
        if value != request_user:
            raise serializers.ValidationError("شما مجاز به استفاده از این کاربر نیستید.")

    def validate(self, data):
        # محاسبه جمع بدهکار و بستانکار
        total_debt = sum(b['amount'] for b in data['items'] if b['transaction_type'] == 'debt')
        total_credit = sum(b['amount'] for b in data['items'] if b['transaction_type'] == 'credit')
        if total_debt != total_credit:
            raise serializers.ValidationError("مجموع بدهکاری و بستانکاری برابر نیست.")
        return data

    @transaction.atomic
    def create(self, instance, validated_data):
        user = self.context['request'].user
        balances_data = validated_data.pop('items', [])
        doc = Document.objects.create(user=user, **validated_data)

        for bal_data in balances_data:
            cheque_data = bal_data.pop('cheque', None)
            cheque_obj = CashierCheque.objects.create(user=user, **cheque_data) if cheque_data else None
            BalanceSheet.objects.create(user=user, document=doc, cheque=cheque_obj, **bal_data)
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        user = self.context['request'].user
        balances_data = validated_data.pop('items', [])

        instance.date_created = validated_data.get('date_created')
        instance.save()

        for bal_data in balances_data:
            cheque_data = bal_data.pop('cheque')
            balance_id = bal_data.pop('id')
            if balance_id:
                balance = BalanceSheet.objects.get(id=balance_id, document=instance)
                for f,v in bal_data.items():
                    setattr(balance, f, v)
                if cheque_data:
                    if balance.cheque:
                        for f, v in cheque_data.items():
                            setattr(balance.cheque, f, v)
                    else:
                        balance.cheque = CashierCheque.objects.get(user=user, **cheque_data)
                else:
                    if balance.cheque:
                        balance.cheque.delete()
                        balance.cheque = None
                balance.save()
            else:
                cheque= None
                if cheque_data:
                    cheque = CashierCheque.objects.create(user=user, **cheque_data)
                BalanceSheet.objects.create(
                    document = instance,
                    user=user,
                    cheque=cheque,
                    **bal_data
                )
        return instance
