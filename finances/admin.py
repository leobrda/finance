from django.contrib import admin
from .models import Category, Transaction

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'workspace')
    list_filter = ('category_type', 'workspace')
    search_fields = ('name',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'category', 'workspace', 'transaction_date', 'status')
    list_filter = ('status', 'workspace', 'category__category_type', 'transaction_date')
    search_fields = ('description', 'notes')
    date_hierarchy = 'transaction_date'