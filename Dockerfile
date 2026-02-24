FROM continuumio/miniconda3:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    swig \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash streamlit_user
WORKDIR /home/streamlit_user

COPY environment_docker.yml .

RUN conda env update -n base -f environment_docker.yml && conda clean -afy

COPY . .

WORKDIR /home/streamlit_user/open-py-cest-mrf
RUN python setup.py install

WORKDIR /home/streamlit_user
RUN chown -R streamlit_user:streamlit_user /home/streamlit_user
USER streamlit_user

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]