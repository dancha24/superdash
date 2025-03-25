from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DeleteView

from apps.transactions.models import Transaction


class TransactionDeleteView(PermissionRequiredMixin, DeleteView):

    permission_required = ("transactions.delete_transaction")

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction, id=pk)
        transaction.delete()
        messages.success(request, 'Transaction Deleted')
        return redirect('transactions')
