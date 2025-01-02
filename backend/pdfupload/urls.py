from django.urls import path
from .views import UploadPDFView
from .views import TestPDFView

urlpatterns = [
    path("upload/", UploadPDFView.as_view(), name="upload_pdf"),
    path("test/", TestPDFView.as_view(), name="test_pdf"),
]
