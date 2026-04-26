import logging
import sys
from base64 import b64encode
from functools import wraps
from os import getenv
from pathlib import Path
from textwrap import dedent

from flask import Flask, request, make_response
from flask_orjson import OrjsonProvider
from loguru import logger
from marshmallow import Schema, fields, ValidationError, EXCLUDE

PDFGS_X_API_KEY = getenv("PDFGS_X_API_KEY", None)
DOCKER = getenv("DOCKER", False)
_IN_TESTING = getenv("PDFGS_IN_TESTING", False) in (True, "true", "True", "TRUE")
_LEVEL = "DEBUG" if _IN_TESTING else "INFO"

logger.remove()
logger.add(
    sys.stderr,
    level=_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>",
)


class _InterceptHandler(logging.Handler):
    """Forward stdlib logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


logging.basicConfig(handlers=[_InterceptHandler()], level=_LEVEL, force=True)
for _name in (
    "werkzeug",
    "flask",
    "flask.app",
    "granian",
    "granian.access",
    "granian.server",
    "asgi",
    "wsgi",
    "selenium",
    "selenium.webdriver.remote.remote_connection",
    "urllib3",
    "urllib3.connectionpool",
):
    _lg = logging.getLogger(_name)
    _lg.handlers = [logging.NullHandler()]
    _lg.propagate = False
    _lg.disabled = True
    _lg.setLevel(logging.CRITICAL + 1)


class PDFRequestSchema(Schema):
    html = fields.String(required=True)

    class Meta:
        unknown = EXCLUDE


def match_x_api_key(header_value) -> bool:
    if header_value == "none":
        # This allows the PDFGS_X_API_KEY environment variable to be set to "none"
        # and be considered as disabled
        return True

    if header_value == PDFGS_X_API_KEY:
        return True
    return False


def render_pdf_b64_using_chrome(html_str: str, instance_folder: Path) -> str:
    from uuid import uuid4
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.print_page_options import PrintOptions

    temp_file = instance_folder / f"{uuid4().hex}.html"
    temp_file.write_text(html_str, encoding="utf-8")
    logger.debug(f"Wrote temp HTML for chromium render: {temp_file.name}")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    service = None

    if DOCKER:
        options.binary_location = "/usr/bin/chromium"
        service = Service(executable_path="/usr/bin/chromedriver")

    print_options = PrintOptions()
    print_options.page_width = 21.0
    print_options.page_height = 29.7

    try:
        logger.debug("Launching headless Chromium")
        driver = webdriver.Chrome(options=options, service=service) if service else webdriver.Chrome(options=options)
        try:
            driver.get(temp_file.as_uri())
            pdf_b64 = driver.print_page(print_options)
            logger.info(f"Chromium rendered PDF for {temp_file.name}")
            return pdf_b64
        finally:
            driver.quit()
            logger.debug("Chromium driver quit")
    finally:
        temp_file.unlink(missing_ok=True)
        logger.debug(f"Removed temp HTML: {temp_file.name}")


def check_api_key(*args_, **kwargs_):
    def check_api_key_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if PDFGS_X_API_KEY:
                logger.debug(f"PDFGS_X_API_KEY defined: {PDFGS_X_API_KEY}")
                if x_api_key := request.headers.get("x-api-key"):
                    if not match_x_api_key(x_api_key):
                        logger.warning("Invalid API key on request")
                        if request.is_json:
                            return {"error": "Invalid API Key!"}, 401
                        else:
                            return "Invalid API Key!", 401

                else:
                    logger.warning("Missing x-api-key header on request")
                    if request.is_json:
                        return {"error": "API Key header not found!"}, 401
                    else:
                        return "API Key header not found!", 401

            return func(*args, **kwargs)

        return inner

    return check_api_key_wrapper(*args_, **kwargs_)


def test_route(app: Flask):
    @app.get("/test")
    def test():
        from markupsafe import Markup

        return Markup(
            dedent(
                """\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Test Post Form</title>
            </head>
            <body>

            <form action="http://localhost:9898/pdf"
                  method="POST"
                  style="display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                <label for="post_url">HTML Content:</label>
                <input type="text" name="post_url" id="post_url" value="http://localhost:9898/pdf">

                <label for="html">HTML Content:</label>
                <textarea name="html" id="html" rows="10" cols="50"></textarea>

                <input type="submit" value="Submit">
            </form>

            <script>
                document.getElementById(`post_url`).addEventListener(`input`, function (e) {
                    const form = e.target.closest(`form`);
                    form.action = e.target.value;
                });
            </script>
            </body>
            </html>
            """
            )
        )

    @app.get("/chromium/test")
    def chromium_test():
        from markupsafe import Markup

        return Markup(
            dedent(
                """\
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Test Post Form</title>
            </head>
            <body>

            <form action="http://localhost:9898/chromium/pdf"
                  method="POST"
                  style="display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                <label for="post_url">HTML Content:</label>
                <input type="text" name="post_url" id="post_url" value="http://localhost:9898/chromium/pdf">

                <label for="html">HTML Content:</label>
                <textarea name="html" id="html" rows="10" cols="50"></textarea>

                <input type="submit" value="Submit">
            </form>

            <script>
                document.getElementById(`post_url`).addEventListener(`input`, function (e) {
                    const form = e.target.closest(`form`);
                    form.action = e.target.value;
                });
            </script>
            </body>
            </html>
            """
            )
        )

    @app.post("/test-api-key")
    @check_api_key
    def test_api_key():
        return "passed"


def create_app():
    app = Flask(__name__)
    app.json = OrjsonProvider(app)

    instance_folder = Path(__file__).parent.parent / "instance"
    instance_folder.mkdir(exist_ok=True)
    logger.info(f"Instance folder ready at {instance_folder}")

    @app.get("/")
    def index():
        logger.debug("GET / hit")
        return "PDF-Generator-Service"

    @app.post("/pdf")
    @check_api_key
    def pdf():
        from weasyprint.text.fonts import FontConfiguration
        from weasyprint import HTML

        logger.info(f"POST /pdf received (is_json={request.is_json})")
        font_config = FontConfiguration()
        schema = PDFRequestSchema()

        if request.is_json:
            try:
                data = schema.load(request.get_json())
            except ValidationError as err:
                logger.warning(f"Validation failed on /pdf JSON: {err.messages}")
                return {"error": err.messages}, 400

            html = data.get("html")

            try:
                rendered_pdf = HTML(string=html).write_pdf(font_config=font_config)
            except Exception as e:
                logger.exception(f"WeasyPrint render failed: {e}")
                return {"error": "System Error!"}, 500

            encoded_pdf = b64encode(rendered_pdf).decode("utf-8")
            logger.info("WeasyPrint render succeeded (json response)")
            return {"pdf": encoded_pdf}

        try:
            data = schema.load(request.form)
        except ValidationError as err:
            logger.warning(f"Validation failed on /pdf form: {err.messages}")
            return {"error": err.messages}, 400

        html = data.get("html")

        try:
            rendered_pdf = HTML(string=html).write_pdf(font_config=font_config)
        except Exception as e:
            logger.exception(f"WeasyPrint render failed: {e}")
            return "System Error!", 500

        logger.info("WeasyPrint render succeeded (binary response)")
        response = make_response(rendered_pdf)
        response.headers["Content-Type"] = "application/pdf"
        return response

    @app.post("/chromium/pdf")
    @check_api_key
    def chromium_pdf():
        from base64 import b64decode

        logger.info(f"POST /chromium/pdf received (is_json={request.is_json})")
        schema = PDFRequestSchema()

        if request.is_json:
            try:
                data = schema.load(request.get_json())
            except ValidationError as err:
                logger.warning(f"Validation failed on /chromium/pdf JSON: {err.messages}")
                return {"error": err.messages}, 400

            html = data.get("html")

            try:
                pdf_b64 = render_pdf_b64_using_chrome(html, instance_folder)
            except Exception as e:
                logger.exception(f"Chromium render failed: {e}")
                return {"error": "System Error!"}, 500

            logger.info("Chromium render succeeded (json response)")
            return {"pdf": pdf_b64}

        try:
            data = schema.load(request.form)
        except ValidationError as err:
            logger.warning(f"Validation failed on /chromium/pdf form: {err.messages}")
            return {"error": err.messages}, 400

        html = data.get("html")

        try:
            pdf_b64 = render_pdf_b64_using_chrome(html, instance_folder)
        except Exception as e:
            logger.exception(f"Chromium render failed: {e}")
            return "System Error!", 500

        logger.info("Chromium render succeeded (binary response)")
        response = make_response(b64decode(pdf_b64))
        response.headers["Content-Type"] = "application/pdf"
        return response

    if _IN_TESTING:
        logger.info("Test routes enabled")
        test_route(app)

    return app


main = create_app()
