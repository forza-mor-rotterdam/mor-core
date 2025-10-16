from config.context import db
from django.conf import settings
from mozilla_django_oidc import auth
from rest_framework.authentication import TokenAuthentication as DRFTokenAuthentication


class OIDCAuthenticationBackend(auth.OIDCAuthenticationBackend):
    def create_user(self, claims):
        email = claims.get("email")
        user = self.UserModel.objects.create_user(email=email)

        # copy name from the claims, if not set fallback to email as first name and empty last name
        user.first_name = claims.get("given_name", claims.get("email"))
        user.last_name = claims.get("family_name", "")

        user.save()

        return user

    def update_user(self, user, claims):
        # copy first and last name from claims, if not set use current first and last name
        # this makes it possible to change the name of the user in the admin when IdP is not given names
        user.first_name = claims.get("given_name", user.first_name)
        user.last_name = claims.get("family_name", user.last_name)
        user.save()

        return user

    def get_userinfo(self, access_token, id_token, payload):
        """Return user details dictionary. The id_token and payload are not used in
        the default implementation, but may be used when overriding this method"""

        # Enable print statement below for debuging the JWT claims
        # print(payload)

        # Enable statements below to call userinfo to get additional information about the user
        # user_response = requests.get(
        #     self.OIDC_OP_USER_ENDPOINT,
        #     headers={"Authorization": "Bearer {0}".format(access_token)},
        #     verify=self.get_settings("OIDC_VERIFY_SSL", True),
        #     timeout=self.get_settings("OIDC_TIMEOUT", None),
        #     proxies=self.get_settings("OIDC_PROXY", None),
        # )
        # user_response.raise_for_status()

        # Make sure always an email claim is available, if not set fallback to upn or username
        payload.update(
            {"email": payload.get("email", payload.get("upn", payload.get("username")))}
        )

        return payload


class TokenAuthentication(DRFTokenAuthentication):
    def authenticate_credentials(self, key):
        with db(settings.READONLY_DATABASE_KEY):
            return super().authenticate_credentials(key)
