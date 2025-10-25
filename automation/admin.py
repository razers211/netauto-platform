from django.contrib import admin
from .models import Device, NetworkTask, TaskResult


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'device_type', 'is_active', 'last_connected', 'created_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('name', 'host', 'description')
    readonly_fields = ('created_at', 'last_connected')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'host', 'device_type', 'description', 'is_active')
        }),
        ('Connection Details', {
            'fields': ('username', 'password', 'port')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_connected'),
            'classes': ('collapse',)
        })
    )


@admin.register(NetworkTask)
class NetworkTaskAdmin(admin.ModelAdmin):
    list_display = ('get_task_type_display', 'device', 'status', 'created_by', 'created_at', 'duration')
    list_filter = ('task_type', 'status', 'created_at')
    search_fields = ('device__name', 'created_by__username')
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'duration')
    
    def duration(self, obj):
        if obj.duration():
            return f"{obj.duration().total_seconds():.2f}s"
        return "-"
    duration.short_description = "Duration"


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ('task', 'success', 'execution_time', 'created_at')
    list_filter = ('success', 'created_at')
    search_fields = ('task__device__name', 'task__task_type')
    readonly_fields = ('task', 'execution_time', 'created_at')
    
    def has_add_permission(self, request):
        return False  # TaskResults are created automatically
