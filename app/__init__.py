from base64 import b64encode
from functools import wraps
from os import getenv
from textwrap import dedent

from flask import Flask, request, make_response
from flask_orjson import OrjsonProvider
from marshmallow import Schema, fields, ValidationError, EXCLUDE

PDFGS_X_API_KEY = getenv("PDFGS_X_API_KEY", None)
PDFGS_IN_TESTING = getenv("PDFGS_IN_TESTING", False)


class PDFRequestSchema(Schema):
    html = fields.String(required=True)

    class Meta:
        unknown = EXCLUDE


def print_logger(msg):
    if PDFGS_IN_TESTING in (True, "true", "True", "TRUE"):
        print(msg)


def match_x_api_key(header_value) -> bool:
    if header_value == "none":
        # This allows the PDFGS_X_API_KEY environment variable to be set to "none"
        # and be considered as disabled
        return True

    if header_value == PDFGS_X_API_KEY:
        return True
    return False


def check_api_key(*args_, **kwargs_):
    def check_api_key_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            if PDFGS_X_API_KEY:
                print_logger(f"PDFGS_X_API_KEY defined: {PDFGS_X_API_KEY}")
                if x_api_key := request.headers.get("x-api-key"):
                    if not match_x_api_key(x_api_key):
                        if request.is_json:
                            return {"error": "Invalid API Key!"}, 401
                        else:
                            return "Invalid API Key!", 401

                else:
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

    @app.post("/test-api-key")
    @check_api_key
    def test_api_key():
        return "passed"


def create_app():
    app = Flask(__name__)
    app.json = OrjsonProvider(app)

    @app.get("/")
    def index():
        return "PDF-Generator-Service"

    @app.post("/pdf")
    @check_api_key
    def pdf():
        from weasyprint.text.fonts import FontConfiguration
        from weasyprint import HTML

        font_config = FontConfiguration()
        schema = PDFRequestSchema()

        if request.is_json:
            try:
                data = schema.load(request.get_json())
            except ValidationError as err:
                return {"error": err.messages}, 400

            html = data.get("html")

            try:
                rendered_pdf = HTML(string=html).write_pdf(font_config=font_config)
            except Exception as e:
                print(e)
                return {"error": "System Error!"}, 500

            encoded_pdf = b64encode(rendered_pdf).decode("utf-8")
            return {"pdf": encoded_pdf}

        try:
            data = schema.load(request.form)
        except ValidationError as err:
            return {"error": err.messages}, 400

        html = data.get("html")

        try:
            rendered_pdf = HTML(string=html).write_pdf(font_config=font_config)
        except Exception as e:
            print(e)
            return "System Error!", 500

        response = make_response(rendered_pdf)
        response.headers["Content-Type"] = "application/pdf"
        return response

    if PDFGS_IN_TESTING in (True, "true", "True", "TRUE"):
        test_route(app)

    return app


main = create_app()
