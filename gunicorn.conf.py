from multiprocessing import cpu_count

from os import getenv

cores = cpu_count()

bind = f"0.0.0.0:{getenv('PDFGS_PORT', 9898)}"
workers = (2 * cores) + 1
wsgi_app = "app:create_app()"
