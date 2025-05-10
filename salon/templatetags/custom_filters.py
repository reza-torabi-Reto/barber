from django import template
from extensions.utils import j_convert_list_appoiment

register = template.Library()

@register.filter(name='j_date')
def j_date(date):
    return j_convert_list_appoiment(date)

@register.filter(name='j_time')
def j_time(time):
    return j_convert_list_appoiment(time, time_only=True)

@register.filter(name='get_services')
def get_services(appointment):
    return ", ".join([service.service.name for service in appointment.selected_services.all()])

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key, [])