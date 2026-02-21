from django.urls import path

from Akounting.apps.accounting.api.image_gallery.views import user_images, upload_image

urlpatterns = [
    path('gallery/', user_images, name='image_gallery'),
    path('upload-image/', upload_image, name='upload_image')
]
