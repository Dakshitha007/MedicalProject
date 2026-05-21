from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import LoginHistory, OTPVerification, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ['email', 'username', 'role', 'is_verified', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'username']
    ordering = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('role', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Status', {'fields': ('is_verified',)}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'phone_number', 'purpose', 'is_verified', 'created_at', 'expires_at', 'sent_via']
    search_fields = ['email', 'phone_number', 'purpose']
    readonly_fields = ['code', 'created_at', 'expires_at']


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['login_identifier', 'successful', 'ip_address', 'created_at']
    search_fields = ['login_identifier', 'user_agent', 'ip_address']
    readonly_fields = ['login_identifier', 'successful', 'ip_address', 'user_agent', 'note']
