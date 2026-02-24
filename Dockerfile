FROM frolvlad/alpine-miniconda3:python3.10

RUN adduser -D precat_user
WORKDIR /home/precat_user

COPY environment.yml .

RUN conda env update -n base -f environment.yml && \
    conda clean -afy

COPY . .

WORKDIR /home/precat_user/open-py-cest-mrf
RUN python setup.py install

WORKDIR /home/precat_user
RUN chown -R precat_user:precat_user /home/precat_user
USER precat_user

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]