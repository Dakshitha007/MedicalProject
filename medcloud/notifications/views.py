from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import AllowAnyAuthenticatedWrite
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related('user').all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, AllowAnyAuthenticatedWrite]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
