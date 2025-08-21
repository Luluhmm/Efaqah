from django.contrib import admin
from .models import Registration
from .views import send_payment_link_email

# Register your models here.

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('firstname', 'lastname', 'email', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('firstname', 'lastname', 'email')


    def save_model(self, request, obj, form, change):
        if 'status' in form.changed_data and obj.status == 'approved':
            success = send_payment_link_email(request, obj)

            if success:
                self.message_user(request, "Registration approved and payment link sent successfully.")
            else:
                self.message_user(request, "Failed to send payment link. Check console for errors.", level='error')
        super().save_model(request, obj, form, change)