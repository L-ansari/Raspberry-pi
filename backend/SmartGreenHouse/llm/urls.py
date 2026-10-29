from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # path('test/',views.test_get,name="test"),
    path('recommend/',views.recommend,name="llm_recommend"),
    path('chat/',views.chat,name="llm_chat"),
    path('status/', views.sensor_status, name='sensor_status'),
]
