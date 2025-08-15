FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    nodejs \
    npm \
 && apt-get clean

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app

#EXPOSE 7860

#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
ENV HOME=/etc/oci
RUN mkdir -p /etc/oci/.oci && chmod 777 /etc/oci/.oci

CMD mkdir -p $HOME/.oci && \
    echo "[DEFAULT]" > $HOME/.oci/config && \
    echo "user=${OCI_USER}" >> $HOME/.oci/config && \
    echo "fingerprint=${OCI_FINGERPRINT}" >> $HOME/.oci/config && \
    echo "key_file=/etc/oci/.oci/${OCI_FILE_NAME}" >> /$HOME/.oci/config && \
    echo "tenancy=${OCI_TENANCY}" >> $HOME/.oci/config && \
    echo "region=${OCI_REGION}" >> $HOME/.oci/config && \
    echo "${OCI_KEY}" > $HOME/.oci/${OCI_FILE_NAME} && \
    chmod 600 $HOME/.oci/${OCI_FILE_NAME} && \
    uvicorn main:app --host 0.0.0.0 --port 7860
