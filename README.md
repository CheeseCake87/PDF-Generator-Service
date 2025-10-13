# PDF-Generator-Service

An API service for generating PDFs from the given html.

## Docker

`cheesecake87/pdf-generator-service:latest`

## How it works

This service uses Flask with WeasyPrint to generate PDFs from given html.

The service listens on port `9898` by default, but can be changed
by setting the environment variable `PDFGS_PORT`. Although it is
recommended to use dockers `--publish` flag, somthing like:

```bash
docker run --publish 127.0.0.1:9898:9898/tcp cheesecake87/pdf-generator-service:latest
```

You would then sit this behind a reverse proxy. Or use it directly from other services.

### Usage

#### Form-Data

```bash
curl -X POST -F "html=<h1>Hello, World!</h1>" http://localhost:9898/pdf
```

This will return a PDF file as Content-Type application/pdf

#### JSON

```bash
curl -X POST -H "Content-Type: application/json" -d '{"html": "<h1>Hello, World!</h1>"}' http://localhost:9898/pdf
```

This will return:

```json
{
  "pdf": "<base64_encoded_pdf>"
}
```

#### Tips ℹ️

When passing in html with css, it's best to use the style tag in the head:

```html
<head>
    ...
    <style>
        .styles-here {
            ...
        }
    </style>
</head>
```

You can adjust the page settings, and add fonts by doing:

```html
<style>
    @page {
        size: A4 !important;
        padding: 0 !important;
        margin: 2rem !important;
    }

    @font-face {
        font-family: 'OpenSans';
        src: url('https://<url_to_font>/OpenSans.ttf') format('truetype');
    }
    
    ...
</style>
```

## Security

If you set the environment variable `PDFGS_X_API_KEY`, this will set the
`/pdf` route
to look for the header `X-API-KEY` and check if it matches the value of
`PDFGS_X_API_KEY`.

```bash
docker run --publish 127.0.0.1:9898:9898/tcp -e PDFGS_X_API_KEY=<your_api_key> cheesecake87/pdf-generator-service:latest
```

### Usage

```bash
curl -X POST -H "X-API-KEY: <your_api_key>" -H "Content-Type: application/json" -d '{"html": "<html_string>"}' http://localhost:9898/pdf
```

## ENV Variables List

- `PDFGS_PORT` - The port to listen on.
- `PDFGS_X_API_KEY` - The API key value to use to secure the `/pdf` route.
- `PDFGS_IN_TESTING` - If set to `true`, the service will enable the `/test` and `/test-api-key` routes.

## Orbiting Documentation

Please see the `WeasyPrint` documentation for more information on how the
passed html works.

[https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html](https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html)
