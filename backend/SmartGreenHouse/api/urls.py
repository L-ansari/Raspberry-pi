"""
URL configuration for SmartGreenHouse project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # path('test/',views.test_get,name="test"),
    path('health_check/',views.health_check,name="health_check"),
    path('sensors/',views.create_sensor_reading),
    path('plants/', views.search_plants, name='plant_search'),
    path('sensors/current/', views.current_sensor_reading, name='sensor_current'),
    path('sensors/history-summary/<str:range>/', views.sensor_history_summary, name='sensor_history_summary'),
    path("sensors/<str:obj_id>/", views.sensor_reading_single, name="sensor_reading_single"),
    path("sensors/history/<str:range>/",views.sensor_reading_history,name="sensor_reading_history"),
    path("sensors/history/del/<str:range>/",views.del_sensor_reading,name="del_readings_by_timerange"),
    path("sensors/del/<str:obj_id>/",views.del_sensor_reading,name="del_sensor_reading_by_id"),
    path("edges/register/", views.register_edge, name="edge_register"),
    path("edges/heartbeat/", views.edge_heartbeat, name="edge_heartbeat"),
    path("edges/", views.list_edges, name="edge_list"),
]
