# thumbnailname.py

import logging
import os.path

from django.conf import settings as project_settings
from django.utils import timezone
from sorl.thumbnail import default
from sorl.thumbnail.base import ThumbnailBackend as SorlThumbnailBackend
from sorl.thumbnail.conf import defaults as default_settings
from sorl.thumbnail.conf import settings
from sorl.thumbnail.images import DummyImageFile, ImageFile

logger = logging.getLogger(__name__)


def get_date_file_path():
    return timezone.now().strftime("%Y/%m/%d")


def get_upload_path(instance, filename):
    return get_upload_path_base(filename)


def get_upload_path_base(filename):
    return os.path.join(
        project_settings.BESTANDEN_PREFIX, get_date_file_path(), filename
    )


class ThumbnailBackend(SorlThumbnailBackend):
    def get_thumbnail(self, file_, geometry_string, **options):
        """
        Returns thumbnail as an ImageFile instance for file with geometry and
        options given. First it will try to get it from the key value store,
        secondly it will create it.
        """
        logger.debug("Getting thumbnail for file [%s] at [%s]", file_, geometry_string)

        if file_:
            source = ImageFile(file_)
        else:
            raise ValueError("falsey file_ argument in get_thumbnail()")

        # preserve image filetype
        if settings.THUMBNAIL_PRESERVE_FORMAT:
            options.setdefault("format", self._get_format(source))

        for key, value in self.default_options.items():
            options.setdefault(key, value)

        # For the future I think it is better to add options only if they
        # differ from the default settings as below. This will ensure the same
        # filenames being generated for new options at default.
        for key, attr in self.extra_options:
            value = getattr(settings, attr)
            if value != getattr(default_settings, attr):
                options.setdefault(key, value)

        name = self._get_thumbnail_filename(source, geometry_string, options)
        thumbnail = ImageFile(name, default.storage)

        # We have to check exists() because the Storage backend does not
        # overwrite in some implementations.
        if settings.THUMBNAIL_FORCE_OVERWRITE or not thumbnail.exists():
            try:
                source_image = default.engine.get_image(source)
            except Exception as e:
                logger.exception(e)
                if settings.THUMBNAIL_DUMMY:
                    return DummyImageFile(geometry_string)
                else:
                    # if storage backend says file doesn't exist remotely,
                    # don't try to create it and exit early.
                    # Will return working empty image type; 404'd image
                    logger.warning(
                        "Remote file [%s] at [%s] does not exist",
                        file_,
                        geometry_string,
                    )
                    return thumbnail

            # We might as well set the size since we have the image in memory
            image_info = default.engine.get_image_info(source_image)
            options["image_info"] = image_info
            size = default.engine.get_image_size(source_image)
            source.set_size(size)

            try:
                self._create_thumbnail(
                    source_image, geometry_string, options, thumbnail
                )
                self._create_alternative_resolutions(
                    source_image, geometry_string, options, thumbnail.name
                )
            finally:
                default.engine.cleanup(source_image)

        # If the thumbnail exists we don't create it, the other option is
        # to delete and write but this could lead to race conditions so I
        # will just leave that out for now.
        return thumbnail

    def _get_thumbnail_filename(self, source, geometry_string, options):
        filename, _ext = os.path.splitext(os.path.basename(source.name))
        filename_full = f"{filename}_{geometry_string}.jpg"
        return os.path.join(
            settings.THUMBNAIL_PREFIX, get_date_file_path(), filename_full
        )
