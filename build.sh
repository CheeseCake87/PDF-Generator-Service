docker build -f Dockerfile -t cheesecake87/pdf-generator-service:b9 --platform linux/amd64 . &&
docker build -f Dockerfile -t cheesecake87/pdf-generator-service:latest --platform linux/amd64 . &&
docker build -f Dockerfile -t cheesecake87/pdf-generator-service-gfonts:b4 --platform linux/amd64 . &&
docker build -f Dockerfile -t cheesecake87/pdf-generator-service-gfonts:latest --platform linux/amd64 .
