from django.urls import include, path

urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('patients/', include('patients.urls')),
    path('doctors/', include('doctors.urls')),
    path('reports/', include('reports.urls')),
    path('appointments/', include('appointments.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('notifications/', include('notifications.urls')),
]
