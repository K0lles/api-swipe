from rest_framework.generics import ListCreateAPIView, DestroyAPIView

from .serializers import *


class AdditionListCreateAPIView(ListCreateAPIView):
    serializer_class = AdditionSerializer
    queryset = Addition.objects.all()

    def list(self, request, *args, **kwargs):
        print(request.user)
        return super().list(request, *args, **kwargs)


class AdditionDestroyAPIView(DestroyAPIView):
    lookup_url_kwarg = 'addition_pk'
    queryset = Addition.objects.all()
