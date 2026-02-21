import uuid


def user_directory_file_path(instance, filename):
    ext = filename.split('.')[-1]
    file = filename.split('.')[1]
    return f'images/{instance.user.id}/{file}-{uuid.uuid4()}.{ext}'