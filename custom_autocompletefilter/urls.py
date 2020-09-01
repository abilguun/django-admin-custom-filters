from django.urls import path

from . import views
from .views import FieldAutoComplete

app_name = '***'
urlpatterns = [
    path('', views.index, name='index'),
    path('field_autocomplete/', FieldAutoComplete.as_view(), name='field_autocomplete'),
]
