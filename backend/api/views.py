from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import MeSerializer

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "email": user.email,
            "role": user.role,
            "tenant": user.tenant.name,
            "tenant_slug": user.tenant.slug,
        }
        return Response(MeSerializer(data).data)
