from django.core.management.base import BaseCommand
from flats.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            Promotion.objects.all().delete()
            PromotionType.objects.all().delete()
            Favorite.objects.all().delete()
            ChessBoardFlat.objects.all().delete()
            ChessBoard.objects.all().delete()
            Photo.objects.all().delete()
            Gallery.objects.all().delete()
            Flat.objects.all().delete()
            ResidentialComplex.objects.all().delete()
            Addition.objects.all().delete()
        except:
            pass
