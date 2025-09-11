from django.urls import path
from . import views

app_name = 'Monitor'

urlpatterns = [
    path('', views.index, name='index'),  # Die bestehende URL für das Dashboard
    path('monitor-data/', views.monitor_data, name='monitor_data'),  # Neue URL für Datenaktualisierung
    path('update_device/', views.update_device, name='update_device'),
]