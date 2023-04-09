import pytest
from pytest_django.fixtures import _django_db_helper

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
                               data={'email': 'simplebuilder@gmail.com', 'password': '123qweasd'},
                               format='json')
    else:
        response = client.post(path='/api/v1/users/auth/login/',
                               data={'email': 'oleksijkolotilo63@gmail.com', 'password': '123qweasd'},
                               format='json')
    return response.data


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


@pytest.mark.django_db_class_scope
class TestingUsers:

    def testing_initializing_filling_db(self, fill_db):
        """
        Method only for filling database with starting data, including users, roles etc.
        :param fill_db:
        :return: None
        """
        pass

    def test_login(self):
        response = client.post('/api/v1/users/auth/login/',
                               {'email': 'oleksijkolotilo63@gmail.com', 'password': '123qweasd'}, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_logout(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
        response = client.post('/api/v1/users/auth/logout/')
        assert response.status_code == status.HTTP_200_OK

    def test_change_password(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
        response = client.post('/api/v1/users/auth/password/change/',
                               data={
                                   'new_password1': '123qweasd',
                                   'new_password2': '123qweasd'
                               })
        assert response.status_code == status.HTTP_200_OK

    def test_get_all_managers(self):
        response = client.get('/api/v1/users/users/managers/')
        assert response.status_code == status.HTTP_200_OK

    def test_blocking_and_unblocking_user(self):
        user_to_block = User.objects.filter(role__role='user').exclude(email='oleksijkolotilo63@gmail.com').first()

        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user("admin").get("access_token")}')
        response = client.post(f'/api/v1/users/users/{user_to_block.id}/block/')
        assert response.status_code == status.HTTP_200_OK

        response = client.post(f'/api/v1/users/users/{user_to_block.id}/unblock/')
        assert response.status_code == status.HTTP_200_OK

    def test_updating_self_account(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
        response = client.patch(path='/api/v1/users/users/me/update/',
                                data={
                                    'name': faker.first_name(),
                                    'surname': faker.last_name(),
                                    'turn_calls_to_agent': True
                                })
        assert response.status_code == status.HTTP_200_OK

    def test_creation_and_deletion_user(self):
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
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_deletion_self_account(self):
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_user().get("access_token")}')
        response = client.delete(path='/api/v1/users/users/me/delete/')
        assert response.status_code == status.HTTP_200_OK
