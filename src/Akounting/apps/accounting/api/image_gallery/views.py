from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from Akounting.apps.accounting.models import Image


@login_required
def user_images(request):
    images = Image.objects.filter(user=request.user)
    return render(request, 'partials/image_modal.html', {'images': images})

@login_required
def upload_image(request):
    if request.method == 'POST':
        image = Image.objects.create(
            user=request.user,
            file=request.FILES['file']
        )
        return JsonResponse({
            'id': image.id,
            'url': image.file.url
        })
