FROM python:3-alpine
COPY repositories /etc/apk/
ADD https://wtnb75-repo.netlify.app/wtnb75@gmail.com-601572c5.rsa.pub /etc/apk/keys/
RUN apk add --no-cache s3fs-fuse davfs2 cifs-utils curlftpfs sshfs mailcap nfs-utils fuseiso squashfuse
RUN addgroup root davfs2
COPY requirements.txt server.py mount_info.yaml /
RUN pip install -r /requirements.txt
CMD ["python", "/server.py"]
LABEL org.opencontainers.image.source https://github.com/wtnb75/docker-volume-anyfs
