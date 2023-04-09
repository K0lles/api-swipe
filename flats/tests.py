import os.path

import pytest
import base64

from pytest_django.fixtures import _django_db_helper

from faker import Faker

from random import choice, randint

from rest_framework import status
from rest_framework.test import APIClient

from flats.models import ResidentialComplex, Addition, ChessBoardFlat, PromotionType
from users.tests import login_user, fill_db
from api_swipe.settings import BASE_DIR


faker = Faker('uk_UA')
client = APIClient()


_django_db_function_scope_helper = pytest.fixture(_django_db_helper.__wrapped__, scope='function')
_django_db_class_scope_helper = pytest.fixture(_django_db_helper.__wrapped__, scope='class')


@pytest.fixture()
def _django_db_helper(request) -> None:
    marker = request.node.get_closest_marker('django_db_class_scope')
    if not marker:
        request.getfixturevalue('_django_db_function_scope_helper')


@pytest.fixture(autouse=True)
def django_db_class_scope_marker(request) -> None:
    marker = request.node.get_closest_marker('django_db_class_scope')
    if marker:
        request.getfixturevalue('_django_db_class_scope_helper')


def get_image() -> bytes:
    """
    Function for returning image in base64 format.
    :return: bytes
    """
    path_to_image = os.path.join(BASE_DIR, 'testing_images/1.jpg')
    with open(path_to_image, 'rb') as image_file:
        image_read = image_file.read()
        image = base64.b64encode(image_read)
        return image


@pytest.mark.django_db_class_scope
class TestingFlatsAndRC:

    def testing_initializing_filling_db(self, fill_db):
        """
        Method only for filling database with starting data, including users, roles etc.
        :param fill_db:
        :return: None
        """
        pass

    def test_residential_complex_create(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
        response = client.post(path='/api/v1/residential-complex/',
                               data={
                                   'photo': get_image(),
                                   'name': faker.company(),
                                   'address': faker.address(),
                                   'map_code': '<div></div>',
                                   'description': faker.catch_phrase(),
                                   'status': choice(['flats', 'cottage', 'many-floors', 'secondary-market']),
                                   'price_for_meter': randint(20, 65),
                                   'min_price': randint(20000, 190000),
                                   'house_type': choice(['cottage', 'many-floors', 'secondary-market']),
                                   'house_class': choice(['lux', 'elite', 'common']),
                                   'building_technology': 'bricks',
                                   'territory_type': choice(['closed', 'opened', 'closed-and-secured']),
                                   'sea_distance': randint(1, 800),
                                   'ceiling_altitude': randint(1, 4),
                                   'gas': True,
                                   'heating': 'centralized',
                                   'electricity': True,
                                   'sewage': 'centralized',
                                   'water_supply': 'centralized',
                                   'arrangement': 'justice',
                                   'payment': choice(['mortgage', 'parent-capital']),
                                   'purpose': 'living-building',
                                   'sum_in_contract': 'full'
                               },
                               format='json')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_documents_get(self):
        response = client.get('/api/v1/documents/my/')
        assert response.status_code == status.HTTP_200_OK

    def test_documents_creation_and_deletion(self):
        response_creation = client.post('/api/v1/documents/my/create/',
                                        data={
                                            'name': faker.name(),
                                            'document': open(os.path.join(BASE_DIR, 'testing_images/1.jpg'), 'rb')
                                        })
        self.document_id = response_creation.data.get('id')  # for further testing of deletion document
        response_deletion = client.delete(f'/api/v1/documents/{self.document_id}/my/delete/')

        assert response_creation.status_code == status.HTTP_201_CREATED and response_deletion.status_code == status.HTTP_204_NO_CONTENT

    def test_addition_create(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("admin").get("access_token")}')
        response = client.post('/api/v1/additions/',
                               data={
                                   'logo': get_image(),
                                   'name': faker.first_name()
                               },
                               format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_adding_and_deletion_addition_to_rc(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
        response_creation = client.post('/api/v1/additions-in-complex/my/create/',
                                        data={
                                            'addition': Addition.objects.first().id,
                                            'turned_on': True
                                        },
                                        format='json')
        addition_id = response_creation.data.get('id')
        assert response_creation.status_code == status.HTTP_201_CREATED

        response_deletion = client.delete(f'/api/v1/additions-in-complex/{addition_id}/my/delete/')
        assert response_deletion.status_code == status.HTTP_204_NO_CONTENT

    def test_corps_floor_and_section_creation(self):
        response_corps = client.post('/api/v1/corps/my/create/')
        response_section = client.post('/api/v1/sections/my/create/')
        response_floor = client.post('/api/v1/floors/my/create/')

        assert response_corps.status_code == status.HTTP_201_CREATED and response_section.status_code == status.HTTP_201_CREATED \
            and response_floor.status_code == status.HTTP_201_CREATED

    def test_flat_creation(self):
        user = login_user("builder")
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.get("access_token")}')
        residential_complex = ResidentialComplex.objects.prefetch_related('corps_set', 'section_set', 'floor_set').get(owner_id=user.get('user').get('pk'))
        response = client.post('/api/v1/flats/my/create/',
                               data={
                                   'corps': residential_complex.corps_set.first().id,
                                   'section': residential_complex.section_set.first().id,
                                   'floor': residential_complex.floor_set.first().id,
                                   'scheme': get_image(),
                                   'district': faker.address(),
                                   'micro_district': faker.address(),
                                   'room_amount': 6,
                                   'square': 145,
                                   'price': 150000,
                                   'condition': 'living-condition'
                               },
                               format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_creation_announcements(self):
        residential_complex = ResidentialComplex.objects.first()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("user").get("access_token")}')
        response = client.post('/api/v1/announcements/create/',
                               data={
                                   "main_photo": get_image(),
                                   "residential_complex": residential_complex.id,
                                   "address": faker.address(),
                                   "purpose": "apartments",
                                   "room_amount": 5,
                                   "planning": "studio-bathroom",
                                   "house_condition": "repair-required",
                                   "overall_square": 180,
                                   "kitchen_square": 43,
                                   "has_balcony": True,
                                   "heating_type": "gas",
                                   "payment_option": "parent-capital",
                                   "agent_commission": 140,
                                   "communication_method": "phone-messages",
                                   "description": "string",
                                   "price": 120000
                               },
                               format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_announcements_to_approve(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
        response = client.get('/api/v1/announcements-approval/requests/')

        assert response.status_code == status.HTTP_200_OK

    def test_approval_announcement(self):
        user = login_user("builder")
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.get("access_token")}')
        residential_complex = ResidentialComplex.objects.prefetch_related('flat_set').get(owner_id=user.get('user').get('pk'))
        announcement = ChessBoardFlat.objects.filter(residential_complex__owner_id=user.get("user").get("pk")).first()
        response = client.patch(f'/api/v1/announcements-approval/{announcement.id}/approve/',
                                data={
                                    'flat': residential_complex.flat_set.first().id,
                                    'accepted': True
                                },
                                format='json')

        assert response.status_code == status.HTTP_200_OK

    def test_promotion_type_creation(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("admin").get("access_token")}')
        response = client.post('/api/v1/promotion-types/',
                               data={
                                   'name': 'testing',
                                   'price': 2.99,
                                   'efficiency': 3
                               },
                               format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_get_promotion_types(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
        response = client.get('/api/v1/promotion-types/')

        assert response.status_code == status.HTTP_200_OK

    def test_promote_announcement(self):
        user = login_user("user")
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {user.get("access_token")}')
        promotion = PromotionType.objects.first()
        announcement = ChessBoardFlat.objects.filter(accepted=True, creator_id=user.get('user').get('pk')).first()
        response = client.post(f'/api/v1/announcement-promotion/?announcement={announcement.id}&promotion_type={promotion.id}',
                               data={
                                   'logo': open(os.path.join(BASE_DIR, 'testing_images/1.jpg'), 'rb'),
                                   'header': faker.catch_phrase(),
                                   'color': 'green',
                               })

        assert response.status_code == status.HTTP_201_CREATED

    def test_calling_off_announcement(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("admin").get("access_token")}')
        announcement = ChessBoardFlat.objects.filter(accepted=True).first()
        response = client.patch(f'/api/v1/announcements/{announcement.id}/call-off/',
                                data={
                                    'rejection_reason': 'incorrect-price',
                                    'called_off': True
                                })

        assert response.status_code == status.HTTP_200_OK

    def test_allowing_announcement(self):
        announcement = ChessBoardFlat.objects.filter(called_off=True).first()
        response = client.patch(f'/api/v1/announcements/{announcement.id}/allow/')

        assert response.status_code == status.HTTP_200_OK
