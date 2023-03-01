from django.urls import path

from .views import AdditionListCreateAPIView, AdditionDestroyAPIView


urlpatterns = [
    path('additions/', AdditionListCreateAPIView.as_view(), name='additions'),
    path('additions/delete/<int:addition_pk>', AdditionDestroyAPIView.as_view(), name='addition-delete'),
]
