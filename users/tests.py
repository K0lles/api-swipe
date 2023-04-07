import pytest
from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.test import APIClient
from faker import Faker

from users.models import User, Role

faker = Faker('uk_UA')

client = APIClient()


@pytest.fixture(scope="function")
def fill_db() -> None:
    """
    Filling database with testing data
    :return: None
    """
    init_scripts()


def init_scripts():
    Role.objects.create(role='admin')
    Role.objects.create(role='user')
    Role.objects.create(role='manager')
    Role.objects.create(role='builder')

    admin = User.objects.create_superuser(
        email='superuser@gmail.com',
        password='123qweasd',
        name='Super',
        surname='User'
    )
    EmailAddress.objects.create(
        user=admin,
        email=admin.email,
        verified=True,
        primary=True
    )

    user = User.objects.create_user(
        email='oleksijkolotilo63@gmail.com',
        password='123qweasd',
        name='User',
        surname='User',
        role=Role.objects.get(role='user')
    )
    EmailAddress.objects.create(
        user=user,
        email=user.email,
        verified=True
    )

    builder = User.objects.create_user(
        email='simplebuilder@gmail.com',
        password='123qweasd',
        name='Builder',
        surname='Builder',
        role=Role.objects.get(role='builder')
    )
    EmailAddress.objects.create(
        user=builder,
        email=builder.email,
        verified=True
    )

    for i in range(0, 5):
        user = User.objects.create_user(
            name=faker.first_name(),
            surname=faker.last_name(),
            email=faker.email(),
            password='123qweasd',
            role=Role.objects.get(role='user')
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True
        )


def login_user(role=None):
    if role == 'admin':
        response = client.post(path='/api/v1/users/auth/login/',
                               data={'email': 'superuser@gmail.com', 'password': '123qweasd'},
                               format='json')
    elif role == 'builder':
        response = client.post(path='/api/v1/users/auth/login/',
                               data={'email': 'simplbuilder@gmail.com', 'password': '123qweasd'},
                               format='json')
    else:
        response = client.post(path='/api/v1/users/auth/login/',
                               data={'email': 'oleksijkolotilo63@gmail.com', 'password': '123qweasd'},
                               format='json')
    return response.data


@pytest.mark.django_db
def test_login(fill_db):
    response = client.post('/api/v1/users/auth/login/',
                           {'email': 'oleksijkolotilo63@gmail.com', 'password': '123qweasd'}, format='json')
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_logout(fill_db):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
    response = client.post('/api/v1/users/auth/logout/')
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_change_password(fill_db):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
    response = client.post('/api/v1/users/auth/password/change/',
                           data={
                               'new_password1': 'helloworld',
                               'new_password2': 'helloworld'
                           })
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_get_all_managers(fill_db):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
    response = client.get('/api/v1/users/users/managers/')
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_blocking_and_unblocking_user(fill_db):
    user_to_block = User.objects.filter(role__role='user').first()

    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("admin").get("access_token")}')
    response = client.post(f'/api/v1/users/users/{user_to_block.id}/block/')
    assert response.status_code == status.HTTP_200_OK

    response = client.post(f'/api/v1/users/users/{user_to_block.id}/unblock/')
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_creation_and_deletion_user(fill_db):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("admin").get("access_token")}')
    response = client.post(path='/api/v1/users/users/',
                           data={
                               'password': '123qweasd',
                               'email': 'test_user@gmail.com',
                               'role': 'user',
                               'name': 'Customed User',
                               'surname': 'Surname'
                           },
                           format='json')
    user_id = response.data.get('id')
    assert response.status_code == status.HTTP_201_CREATED

    response = client.delete(path=f'/api/v1/users/users/{user_id}/')
    client.credentials()
    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_updating_self_account(fill_db):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("user").get("access_token")}')
    response = client.patch(path='/api/v1/users/users/me/update/',
                            data={
                                'name': faker.first_name(),
                                'surname': faker.last_name()
                            })
    client.credentials()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_deletion_self_account(fill_db):
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("user").get("access_token")}')
    response = client.delete(path='/api/v1/users/users/me/delete/')
    client.credentials()
    assert response.status_code == status.HTTP_200_OK
