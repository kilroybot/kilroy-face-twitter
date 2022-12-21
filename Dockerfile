ARG MINICONDA_IMAGE_TAG=4.10.3

FROM continuumio/miniconda3:$MINICONDA_IMAGE_TAG AS base

WORKDIR /app/

# install poetry
COPY ./requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache \
    python3 -m pip install -r ./requirements.txt

# create new environment
# warning: for some reason conda can hang on "Executing transaction" for a couple of minutes
COPY environment.yaml ./environment.yaml
RUN --mount=type=cache,target=/opt/conda/pkgs \
    conda env create -f ./environment.yaml

# "activate" environment for all commands (note: ENTRYPOINT is separate from SHELL)
SHELL ["conda", "run", "--no-capture-output", "-n", "kilroy-face-twitter", "/bin/bash", "-c"]

WORKDIR /app/kilroy_face_twitter/

# add poetry files
COPY ./kilroy_face_twitter/pyproject.toml ./kilroy_face_twitter/poetry.lock ./

FROM base AS test

# install dependencies only (notice that no source code is present yet)
RUN --mount=type=cache,target=/root/.cache \
    poetry install --no-root --only main,test

# add source, tests and necessary files
COPY ./kilroy_face_twitter/src/ ./src/
COPY ./kilroy_face_twitter/tests/ ./tests/
COPY ./kilroy_face_twitter/LICENSE ./kilroy_face_twitter/README.md ./

# build wheel by poetry and install by pip (to force non-editable mode)
RUN poetry build -f wheel && \
    python -m pip install --no-deps --no-index --no-cache-dir --find-links=dist kilroy-face-twitter

ENV TORCH_HOME=/etc/torch
RUN kilroy-face-twitter-fetch-models

# add entrypoint
COPY ./entrypoint.sh ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh", "pytest"]
CMD []

FROM base AS production

# install dependencies only (notice that no source code is present yet)
RUN --mount=type=cache,target=/root/.cache \
    poetry install --no-root --only main

# add source and necessary files
COPY ./kilroy_face_twitter/src/ ./src/
COPY ./kilroy_face_twitter/LICENSE ./kilroy_face_twitter/README.md ./

# build wheel by poetry and install by pip (to force non-editable mode)
RUN poetry build -f wheel && \
    python -m pip install --no-deps --no-index --no-cache-dir --find-links=dist kilroy-face-twitter

ENV TORCH_HOME=/etc/torch
RUN kilroy-face-twitter-fetch-models

# add entrypoint
COPY ./entrypoint.sh ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh", "kilroy-face-twitter"]
CMD []
