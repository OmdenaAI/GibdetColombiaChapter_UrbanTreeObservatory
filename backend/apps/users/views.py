from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):
    """The logged-in user: the frontend shows its name and, to staff users, the
    Reports page."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "username": user.get_username(),
                "name": user.get_full_name(),
                "is_staff": user.is_staff,
            }
        )
