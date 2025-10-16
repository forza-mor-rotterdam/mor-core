class BasisFout(Exception):
    message_type = "Onbende fout"

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "%s: %s" % (self.message_type, self.message)


class UrlFout(BasisFout):
    message_type = "Url fout"
