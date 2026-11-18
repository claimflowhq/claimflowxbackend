from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ClaimViewSet, DashboardMetricsView

router = DefaultRouter()
router.register(r'', ClaimViewSet, basename='claim')

urlpatterns = [
    path('dashboard/metrics/', DashboardMetricsView.as_view(), name='claims-dashboard-metrics'),
] + router.urls

