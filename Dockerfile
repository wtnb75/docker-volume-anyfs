FROM python:3-alpine
COPY repositories /etc/apk/
ADD http://wtnb75-repo.s3-website-ap-northeast-1.amazonaws.com/wtnb75@gmail.com-601572c5.rsa.pub /etc/apk/keys/
COPY requirements.txt server.py mount_info.yaml /
RUN apk add --no-cache s3fs-fuse davfs2 cifs-utils curlftpfs sshfs mailcap nfs-utils fuseiso squashfuse && \
    addgroup root davfs2 && \
    pip install --no-cache-dir -r /requirements.txt
CMD ["python", "/server.py"]
LABEL org.opencontainers.image.source https://github.com/wtnb75/docker-volume-anyfs
