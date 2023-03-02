from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AdditionAPIViewSet, ResidentialComplexAPIViewSet

router = DefaultRouter()
router.register('residential-complex', ResidentialComplexAPIViewSet, basename='residential-complex')
router.register('additions', AdditionAPIViewSet, basename='additions')


urlpatterns = [
    path('', include(router.urls)),
    # path('additions/', AdditionListCreateAPIView.as_view(), name='additions'),
    # path('additions/delete/<int:addition_pk>', AdditionDestroyAPIView.as_view(), name='addition-delete'),
]
