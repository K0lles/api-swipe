from django.contrib.auth.forms import SetPasswordForm
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError


class CustomSetPasswordForm(SetPasswordForm):

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        if len(password1) < 5:
            raise ValidationError(
                {'detail': _('Пароль занадто короткий')},
                code='password_short'
            )
        return password2
