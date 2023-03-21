from flats.models import Photo


def update_gallery_photos(instance, gallery_photos, use_sequence=False):
    remove_items_gallery = {item.id: item for item in instance.gallery.photo_set.all()}

    if gallery_photos:
        for index, item in enumerate(gallery_photos):
            item_id = item.get('id', None)

            if not item_id:
                if use_sequence:
                    Photo.objects.create(gallery=instance.gallery,
                                         sequence_number=index,
                                         **item)
                else:
                    Photo.objects.create(gallery=instance.gallery,
                                         **item)
            elif remove_items_gallery.get(item_id, None) is not None:
                item_instance: Photo = remove_items_gallery.pop(item_id, None)
                item.pop('id')      # delete 'id' field in order to avoid altering of primary key field in db
                if use_sequence:
                    if item_instance.sequence_number != index or item.get('photo', None):
                        Photo.objects.filter(id=item_instance.id).update(sequence_number=index,
                                                                         **item)
                else:
                    if item.get('photo', None):
                        Photo.objects.filter(id=item_instance.id).update(**item)

        instance.gallery.refresh_from_db(fields=['photo_set'])  # refresh prefetch_related photo_set
