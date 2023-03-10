from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'residential-complex', ResidentialComplexAPIViewSet, basename='residential-complex')
router.register(r'additions', AdditionAPIViewSet, basename='additions')
router.register(r'corps', CorpsAPIViewSet, basename='corps')
router.register(r'documents', DocumentAPIViewSet, basename='documents')


urlpatterns = [
    path('', include(router.urls)),
]
