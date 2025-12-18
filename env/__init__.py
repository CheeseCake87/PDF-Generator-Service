from os import getenv, environ


def load():
    host = "0.0.0.0"
    port = getenv("PDFGS_PORT", 9898)

    environ["GRANIAN_HOST"] = host
    environ["GRANIAN_PORT"] = str(port)
    environ["GRANIAN_WORKERS"] = str(1)
    environ["GRANIAN_INTERFACE"] = "wsgi"
    environ["GRANIAN_BACKPRESSURE"] = str(20)
