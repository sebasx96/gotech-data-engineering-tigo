FROM quay.io/jupyter/minimal-notebook:latest

COPY --chown=${NB_UID}:${NB_GID} \
    requirements.txt \
    /tmp/project-requirements.txt

RUN pip install --no-cache-dir \
    -r /tmp/project-requirements.txt \
    && fix-permissions "${CONDA_DIR}" \
    && fix-permissions "/home/${NB_USER}"