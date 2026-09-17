from django.contrib import admin
from .models import Workspace

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace_type', 'user', 'created_at')
    list_filter = ('workspace_type', 'user')
    search_fields = ('name', 'user__username')