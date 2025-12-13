FROM python:3.12 AS base
WORKDIR /app

FROM base AS build
COPY . /app
RUN pip install -e .
ENTRYPOINT ["gitx"]