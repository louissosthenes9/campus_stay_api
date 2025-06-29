from django.contrib import admin
from .models import Enquiry, EnquiryMessage, EnquiryStatus

class EnquiryMessageInline(admin.TabularInline):
    model = EnquiryMessage
    extra = 0
    readonly_fields = ('created_at', 'sender', 'content', 'is_read')
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'property_title', 'student_name', 'property_owner', 'status', 'is_active', 'created_at')
    list_filter = ('status', 'is_active', 'created_at', 'updated_at')
    search_fields = ('property__title', 'student__user__email', 'student__user__first_name', 'student__user__last_name')
    list_select_related = ('property', 'student__user', 'property__user')
    readonly_fields = ('created_at', 'updated_at', 'student', 'property')
    inlines = [EnquiryMessageInline]
    
    fieldsets = (
        (None, {
            'fields': ('property', 'student', 'status', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def student_name(self, obj):
        return f"{obj.student.user.get_full_name()}" if obj.student else "-"
    student_name.short_description = 'Student'
    
    def property_owner(self, obj):
        return f"{obj.property.user.get_full_name()}" if obj.property and obj.property.user else "-"
    property_owner.short_description = 'Property Owner'
    
    def property_title(self, obj):
        return obj.property.title if obj.property else "-"
    property_title.short_description = 'Property'

@admin.register(EnquiryMessage)
class EnquiryMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'enquiry_id', 'sender_name', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('content', 'sender__email', 'enquiry__id')
    list_select_related = ('enquiry', 'sender')
    readonly_fields = ('created_at', 'enquiry', 'sender', 'content')
    
    def sender_name(self, obj):
        return obj.sender.get_full_name() if obj.sender else "-"
    sender_name.short_description = 'Sender'
    
    def enquiry_id(self, obj):
        return f"Enquiry #{obj.enquiry.id}" if obj.enquiry else "-"
    enquiry_id.short_description = 'Enquiry'
