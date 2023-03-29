from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r'residential-complex', ResidentialComplexAPIViewSet, basename='residential-complex')
router.register(r'additions', AdditionAPIViewSet, basename='additions')
router.register(r'additions-in-complex', AdditionInComplexAPIViewSet, basename='additions-in-complex')
router.register(r'corps', CorpsAPIViewSet, basename='corps')
router.register(r'documents', DocumentAPIViewSet, basename='documents')
router.register(r'news', NewsAPIViewSet, basename='news')
router.register(r'flats', FlatAPIViewSet, basename='flats')
router.register(r'sections', SectionAPIViewSet, basename='sections')
router.register(r'photo', PhotoAPIDeleteViews, basename='photo')
router.register(r'floors', FloorAPIViewSet, basename='floors')
router.register(r'promotion-types', PromotionTypeAPIViewSet, basename='promotion-types')
router.register(r'chessboards', ChessBoardAPIViewSet, basename='chessboards')
router.register(r'announcements', ChessBoardFlatAnnouncementAPIViewSet, basename='announcements')
router.register(r'announcements-approval', ChessBoardFlatApprovingAPIViewSet, basename='announcements-approve')


urlpatterns = [
    path('', include(router.urls))
]
