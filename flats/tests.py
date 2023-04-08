import os.path

import pytest
import base64

from faker import Faker

from random import choice, randint

from rest_framework import status
from rest_framework.test import APIClient

from flats.models import ResidentialComplex, Gallery
from users.models import User
from users.tests import login_user, fill_db, init_scripts
from api_swipe.settings import BASE_DIR


faker = Faker('uk_UA')
client = APIClient()


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


@pytest.fixture(scope="function")
def fill_residential_complex() -> None:
    """
    Function to create RC for further testing.
    :return: None
    """
    owner = User.objects.get(pk=login_user("builder")["user"]["pk"])
    ResidentialComplex.objects.create(
        owner=owner,
        name=faker.company(),
        photo='init_scripts/residential_complex/1.jpg',
        address=faker.address(),
        map_code='<div></div>',
        description=faker.catch_phrase(),
        status=choice(['flats', 'cottage', 'many-floors', 'secondary-market']),
        price_for_meter=randint(20, 65),
        min_price=randint(20000, 190000),
        house_type=choice(['cottage', 'many-floors', 'secondary-market']),
        house_class=choice(['lux', 'elite', 'common']),
        building_technology='bricks',
        territory_type=choice(['closed', 'opened', 'closed-and-secured']),
        sea_distance=randint(1, 800),
        ceiling_altitude=randint(1, 4),
        gas=True,
        heating='centralized',
        electricity=True,
        sewage='centralized',
        water_supply='centralized',
        arrangement='justice',
        payment=choice(['mortgage', 'parent-capital']),
        purpose='living-building',
        sum_in_contract='full',
        gallery=Gallery.objects.create()
    )


@pytest.mark.django_db
def test_residential_complex_creation(fill_db):
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
    client.credentials()
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_documents_get(fill_db, fill_residential_complex):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
    response = client.get('/api/v1/documents/my/')
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_documents_create(fill_db, fill_residential_complex):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
    response = client.post('/api/v1/documents/my/create/',
                           data={
                               'name': faker.name(),
                               'document': open(os.path.join(BASE_DIR, 'testing_images/1.jpg'), 'rb')
                           })
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_documents_delete(fill_db, fill_residential_complex):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
    creation_response = client.post('/api/v1/documents/my/create/',
                                    data={
                                        'name': faker.name(),
                                        'document': open(os.path.join(BASE_DIR, 'testing_images/1.jpg'), 'rb')
                                    })
    document_id = creation_response.data.get('id', None)
    response = client.delete(f'/api/v1/documents/{document_id}/my/delete/')
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_addition_create(fill_db, fill_residential_complex):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("builder").get("access_token")}')
    response = client.post('/api/v1/addition/my/create/',
                           data={
                               'name': faker.name(),
                               'document': open(os.path.join(BASE_DIR, 'testing_images/1.jpg'), 'rb')
                           })
    client.credentials()
    assert response.status_code == status.HTTP_200_OK
