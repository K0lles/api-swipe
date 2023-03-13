from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'residential-complex', ResidentialComplexAPIViewSet, basename='residential-complex')
router.register(r'additions', AdditionAPIViewSet, basename='additions')
router.register(r'corps', CorpsAPIViewSet, basename='corps')
router.register(r'documents', DocumentAPIViewSet, basename='documents')
router.register(r'news', NewsAPIViewSet, basename='news')
router.register(r'flats', FlatAPIViewSet, basename='flats')
router.register(r'sections', SectionAPIViewSet, basename='sections')
router.register(r'floors', FloorAPIViewSet, basename='floors')


urlpatterns = [
    path('', include(router.urls)),
]
